import dataclasses
import datetime

import kopf
import pytz
import yaml
import kubernetes
import time
from jinja2 import Environment, FileSystemLoader

GROUP = 'otus.homework'
VERSION = 'v1'
NAME = 'mysqls'


def wait_until_job_end(jobname):
    api = kubernetes.client.BatchV1Api()
    job_finished = False
    jobs = api.list_namespaced_job('default')
    while (not job_finished) and \
            any(job.metadata.name == jobname for job in jobs.items):
        time.sleep(1)
        jobs = api.list_namespaced_job('default')
        for job in jobs.items:
            if job.metadata.name == jobname:
                print(f"job with {jobname} found,wait untill end")
                if job.status.succeeded == 1:
                    print(f"job with {jobname}  success")
                    job_finished = True


def render_template(filename, vars_dict):
    env = Environment(loader=FileSystemLoader('./templates'))
    template = env.get_template(filename)
    yaml_manifest = template.render(vars_dict)
    json_manifest = yaml.full_load(yaml_manifest)
    return json_manifest


def delete_success_jobs(mysql_instance_name):
    print("start deletion")
    jobs_list = [
        f'backup-{mysql_instance_name}-job',
        f'restore-{mysql_instance_name}-job',
        f'change-password-{mysql_instance_name}-job',
    ]
    api = kubernetes.client.BatchV1Api()
    jobs = api.list_namespaced_job('default')
    for job in jobs.items:
        jobname = job.metadata.name
        if jobname in jobs_list:
            if job.status.succeeded == 1:
                api.delete_namespaced_job(jobname,
                                          'default',
                                          propagation_policy='Background')


def set_custom_object_status(obj_params: dict, status: dict):
    custom_object = kubernetes.client.CustomObjectsApi()
    custom_object.patch_namespaced_custom_object_status(
        **obj_params,
        body=status,
    )


@kopf.on.create(GROUP, VERSION, NAME)
# Функция, которая будет запускаться при создании объектов тип MySQL:
def mysql_on_create(body: kopf.Body, name, namespace, **_):
    image = body['spec']['image']
    password = body['spec']['password']
    database = body['spec']['database']
    storage_size = body['spec']['storage_size']

    # Генерируем JSON манифесты для деплоя
    persistent_volume = render_template('mysql-pv.yml.j2',
                                        {'name': name,
                                         'storage_size': storage_size})
    persistent_volume_claim = render_template('mysql-pvc.yml.j2',
                                              {'name': name,
                                               'storage_size': storage_size})
    service = render_template('mysql-service.yml.j2', {'name': name})

    deployment = render_template('mysql-deployment.yml.j2', {
        'name': name,
        'image': image,
        'password': password,
        'database': database})
    restore_job = render_template('restore-job.yml.j2', {
        'name': name,
        'image': image,
        'password': password,
        'database': database})

    # Определяем, что созданные ресурсы являются дочерними к управляемому CustomResource:
    kopf.append_owner_reference(persistent_volume, owner=body)
    kopf.append_owner_reference(persistent_volume_claim, owner=body)  # addopt
    kopf.append_owner_reference(service, owner=body)
    kopf.append_owner_reference(deployment, owner=body)
    # ^ Таким образом при удалении CR удалятся все, связанные с ним pv,pvc,svc, deployments

    api = kubernetes.client.CoreV1Api()

    # Создаем mysql PV:
    api.create_persistent_volume(persistent_volume)
    # Создаем mysql PVC:
    api.create_namespaced_persistent_volume_claim('default', persistent_volume_claim)

    # Создаем mysql SVC:
    api.create_namespaced_service('default', service)

    # Создаем mysql Deployment:
    api = kubernetes.client.AppsV1Api()
    api.create_namespaced_deployment('default', deployment)

    # Пытаемся восстановиться из backup
    is_restored = False
    try:
        api = kubernetes.client.BatchV1Api()
        api.create_namespaced_job('default', restore_job)
    except kubernetes.client.rest.ApiException:
        pass
    else:
        is_restored = True

    # Cоздаем PVC и PV для бэкапов:
    try:
        backup_pv = render_template('backup-pv.yml.j2', {'name': name})
        api = kubernetes.client.CoreV1Api()
        api.create_persistent_volume(backup_pv)
    except kubernetes.client.rest.ApiException:
        pass

    try:
        backup_pvc = render_template('backup-pvc.yml.j2', {'name': name})
        api = kubernetes.client.CoreV1Api()
        api.create_namespaced_persistent_volume_claim('default', backup_pvc)
    except kubernetes.client.rest.ApiException:
        pass

    # Устанавливаем статус Subresource
    restore_verb = 'without' if not is_restored else 'with'
    custom_object_params = dict(
        group=GROUP,
        version=VERSION,
        namespace=namespace,
        plural=NAME,
        name=name,
    )
    new_status = {
        'status': {
            'kind': '',
            'mysql_on_create': {
                'message': f'{name} created {restore_verb} restore-job'
            }
        }
    }
    set_custom_object_status(custom_object_params, new_status)


@kopf.on.delete(GROUP, VERSION, NAME)
def delete_object_make_backup(body, name, **_):
    image = body['spec']['image']
    password = body['spec']['password']
    database = body['spec']['database']

    delete_success_jobs(name)

    # Cоздаем backup job:
    api = kubernetes.client.BatchV1Api()
    backup_job = render_template('backup-job.yml.j2', {
        'name': name,
        'image': image,
        'password': password,
        'database': database})
    api.create_namespaced_job('default', backup_job)
    wait_until_job_end(f"backup-{name}-job")

    # Удаляем mysql PV:
    api = kubernetes.client.CoreV1Api()
    api.delete_persistent_volume(f"{name}-pv")

    return {'message': "mysql and its children resources deleted"}


@kopf.on.update(GROUP, VERSION, NAME)
def update_object_change_password(body, spec, old, new, name, namespace, **_):
    old_password = old['spec']['password']
    new_password = new['spec']['password']
    if old_password != new_password:
        # Создаем Job на изменение пароля
        try:
            change_password_job = render_template(
                'change-password-job.yml.j2',
                dict(
                    name=name,
                    old_password=old_password,
                    new_password=new_password,
                )
            )
            api = kubernetes.client.BatchV1Api()
            api.create_namespaced_job('default', change_password_job)
            wait_until_job_end(f'change-password-{name}-job')
        except kubernetes.client.exceptions.ApiException as exc:
            kopf.exception(
                body,
                reason='Password changing',
                message=f"Change password failed with exception: {exc}",
            )
        else:
            # Если Job не вызвала ошибок - обновляем деплоймент
            api = kubernetes.client.AppsV1Api()
            deployment = render_template(
                'mysql-deployment.yml.j2',
                {
                    'name': name,
                    'image': spec['image'],
                    'password': new_password,
                    'database': spec['database'],
                }
            )
            deployment['spec']['template']['metadata']['annotations'] = {
                "kubectl.kubernetes.io/restartedAt": datetime.datetime.utcnow()
                .replace(tzinfo=pytz.UTC)
                .isoformat()
            }
            api.patch_namespaced_deployment(
                name=name,
                namespace=namespace,
                body=deployment,
            )
            kopf.info(
                body,
                reason='Password changing',
                message='MySQL password has been successfully changed.',
            )
