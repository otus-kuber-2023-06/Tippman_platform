# Tippman_platform

## ДЗ №1

---

### В процессе сделано:
- Собран и загружен в докер-хаб образ [tippman/kubernetes-intro](https://hub.docker.com/repository/docker/tippman/kubernetes-intro/general)
- Добавлен манифест `web-pod.yaml` для создания пода `web`. Под также содержит init контейнер для генерации страницы `index.html` и `volumes`.
- Собран и заружен в докер-хаб образ [tippman/hipster-shop-frontend](https://hub.docker.com/repository/docker/tippman/hipster-shop-frontend/general)
- Автоматически сгенерирован манифест `frontend-pod.yaml` для запуска пода с этим образом.
- Исправлен первоначальный запуск по сгенерированному манифесту `frontend-pod.yaml` (в контейнере отсутствовали переменные среды). Исправлены манифест называется `frontend-pod-healthy.yaml`.

В контейнере frontend отсутствовали переменные среды:
- PRODUCT_CATALOG_SERVICE_ADDR
- CURRENCY_SERVICE_ADDR
- CART_SERVICE_ADDR
- RECOMMENDATION_SERVICE_ADDR
- CHECKOUT_SERVICE_ADDR
- SHIPPING_SERVICE_ADDR
- AD_SERVICE_ADDR

_Вопрос: Разберитесь почему все pod в namespace kube-system восстановились после удаления. Укажите причину в описании PR_

**Ответ:**  
Поды неймспейса kube-system (за исключением `coredns`) - это static поды, которые управляются kubelet на основе манифестов:
```shell
docker@minikube:~$ ll /etc/kubernetes/manifests/
total 28
drwxr-xr-x 1 root root 4096 Jul 10 11:12 ./
drwxr-xr-x 1 root root 4096 Jul 10 11:12 ../
-rw------- 1 root root 2309 Jul 10 11:12 etcd.yaml
-rw------- 1 root root 4071 Jul 10 11:12 kube-apiserver.yaml
-rw------- 1 root root 3390 Jul 10 11:12 kube-controller-manager.yaml
-rw------- 1 root root 1436 Jul 10 11:12 kube-scheduler.yaml
```
Под `coredns` контролируется ReplicaSet, который будет поддерживать в "живом" состоянии все заданные поды.  
> A ReplicaSet ensures that a specified number of pod replicas are running at any given time...
```shell
kuber@kuber-server:~$ kubectl describe pods -n kube-system 
Name:                 coredns-787d4945fb-h2vxr
Namespace:            kube-system
Priority:             2000000000
Priority Class Name:  system-cluster-critical
Service Account:      coredns
...
Controlled By:  ReplicaSet/coredns-787d4945fb
...
```

## ДЗ №2

---

### В процессе сделано:
  - Развернут кластер с помощью kind с 3 master и 3 worker нодами.
  - Создан манифест с типом `ReplicaSet` **frontend-replicaset.yaml**.
  - Исправлены ошибки в манифесте. Отсутствовал блок `selector labels`
  - Попробовал вручную через команду увеличить количество реплик: 
    ```
    kubectl scale replicaset frontend --replicas=3
    ``` 
  - Изменена версия образа из которого `ReplicaSet` поднимает под. После применения манифеста убеждаемся, что образ с которого будут создаваться реплики подов изменился на указанную нами в манифесте версию
    ```
    $ kubectl get replicaset frontend -o=jsonpath='{.spec.template.spec.containers[0].image}'
    tippman/hipster-shop-frontend:v0.0.2
    ```
  - Добавлен `Probes` для `frontend.`
  - Добавлены `Deployment` манифесты для `paymentservice` с двумя стратегиями:
    - Аналог blue-green:
      ```
        strategy:
          rollingUpdate:
            maxUnavailable: 0
            maxSurge: 100%
      ```
    - Reverse Rolling Update:
      ```
        strategy:
          type: RollingUpdate
          rollingUpdate:
            maxUnavailable: 33%
            maxSurge: 0
      ```

  - Добавлен `DaemonSet` `node-exporter-daemonset.yaml`.
  - Чтобы `DaemonSet` мог разворачивать поды на мастер нодах нужно добавить блок `tolerations`:
    ```
        spec:
          tolerations:
            - key: node-role.kubernetes.io/control-plane
              operator: Exists
              effect: NoSchedule
            - key: node-role.kubernetes.io/master
              operator: Exists
              effect: NoSchedule
       ```
