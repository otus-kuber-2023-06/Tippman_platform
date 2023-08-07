# Использование chartmuseum в качестве репозитория

- Спуллить или собрать helm package:
    ```shell
    helm package <chart path>
    ```
    или
    ```shell
    helm pull <public chart repo>/<chart>
    ```
- Загрузить package на собственный `chartmuseum` сервер
  ```shell
  curl --data-binary "@<package>-<version>.tgz" https://chartmuseum.158.160.32.101.nip.io/api/charts
  ```
- Добавить собственный репозиторий в helm:
  ```shell
  helm repo add <new repo name> https://chartmuseum.158.160.32.101.nip.io/
  ```
- Установить package из собственного репозитория:
  ```shell
  helm upgrade --install <release name> <new repo name>/<package> --namespace <namespace> --create-namespace
  ```
- Проверить установку:
    ```shell
    helm list --namespace=<namespace>
    ```
