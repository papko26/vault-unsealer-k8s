# vault-unsealer-k8s
### Наколенный "распаковщик" для vault.

Мульти-инстанс vault в кубере и его ручная распоковка приносит страдания. Это инструмент для автоматизации, vault autounsealing в kubernetes.

#### Принцип работы:

При запуске ожидает поочерёдный ввод ключей в stdin. Ключи никуда не записывает, хранит в RAM до перезапуска.
После их получения проверяет статус vault каждые 30 секунд, в случает если vault запаковался (sealed), распаковывает.
Подробно логгирует каждый шаг в stdout.

#### Установка:
```

vault-unsealer-k8s/src/ # docker build -t vault-unsealer .
vault-unsealer-k8s/src/ # docker push <MY_REGISTRY>/vault-unsealer
vault-unsealer-k8s/manifests/ # поменяй  MY_REGISTRY и MY_REGISTRY_SECRET на свои данные
vault-unsealer-k8s/manifests/ # kubectl apply -f unsealer.yaml
```

#### Обязательные аргументы:
```
VAULT_HEADLESS_SVC
String, headless адрес (тот который просто отдаёт DNS всех подов) vault сервера.
Например VAULT_HEADLESS_SVC="stage-vault-internal"
```
```
KEYS_QUORUM
int, количество shamir ключей, которых достаточно для распаковки
Например KEYS_QUORUM=3
```
```
ZABBIX_PORT
int, порт заббикс-сервера
Например ZABBIX_PORT=10051
```
```
ZABBIX_SERVER
str, адрес заббикс-сервера
Например ZABBIX_SERVER="zabbix.xxx.ru"
```
```
ZABBIX_ITEM
str, название сервиса в заббиксе:
Например ZABBIX_ITEM=unsealer_stage
Название метрики в заббиксе:
unsealer_is_alive
```
#### Процедура ввода ключей:

Подразумевается, что распаковщик работает в kubernetes, как и vault.
Ввести ключи можно только непосредственно в сам под (сделано из соображений безопасности), процедура такая:

##### Зааттачимся (attach, не exec) в процесс ансиллера:
```
papko@phome:~$ kubectl -n vault attach -i vault-unsealer-stage
If you don't see a command prompt, try pressing enter.
```


#### Введём ключи. STDIN виден не будет.
```
0/3 keys are populated
key: 
1/3 keys are populated
key: 
2/3 keys are populated
key: 
3/3 keys are populated

All keys are populated
Starting unseal control loop

Vault node 0 is not sealed
Vault node 1 is not sealed
Vault node 2 is not sealed



Vault node 0 is not sealed
Vault node 1 is not sealed
Vault node 2 is not sealed
```
#### Отключимся
Зажать Ctrl потом поочерёдно P и Q, Можно просто Ctrl+c Он всё подскажет.
...
#### Лайвчеки:

Создаёт файл /tmp/inloop, если получил ключи, и начал луп проверок.

#### Известные проблемы:

* При введении ключей, нет возможности вводить их одновременно (например, когда их одновременно вводят несколько человек). Проблема связана с тем, что для ввода ключей используется attach, то есть все пользователи попажают одновременно в один tty. Как проблему исправить без реализации веб-сервера непонятно. Усложнять логику не хочу, больше компонентов - больше дыр.
* Заббикс не нужон. Нужон пром, нужно сделать, PR приветствуются.
* Имеет смысл проверять на readinessProbe, чтобы можно было контролировать, получил ли он ключи или нет. Нужно реализовать.
