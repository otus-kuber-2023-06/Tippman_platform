# Tippman_platform

## Задание 1

---
_Разберитесь почему все pod в namespace kube-system восстановились после удаления. Укажите причину в описании PR_

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

## Задание с *

---
В контейнере frontend отсутствовали переменные среды:
- PRODUCT_CATALOG_SERVICE_ADDR
- CURRENCY_SERVICE_ADDR
- CART_SERVICE_ADDR
- RECOMMENDATION_SERVICE_ADDR
- CHECKOUT_SERVICE_ADDR
- SHIPPING_SERVICE_ADDR
- AD_SERVICE_ADDR