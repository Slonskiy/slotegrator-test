# Exercise 1

1. Dockerfile<br>
a) Мы планинуем собрать JS приложение, и у нас есть 'package.json' помимо исходного когда приложения. Поэтому я предполагаю в качестве базового образа Docker использовать node, а не nginx. Например я возьму последнюю версию официального node образа. 
Возможно просто установить node в образ с nginx, но мне кажется это не самая хорошая идея, например по соображениям безопасности. Если мы не хотим использовать веб-сервер node для ответов на запросы к нашему приложению, то мне кажтся логичным вынести ingress как отдельный сервис. Кроме того, философия докера: "один процесс - один контейнер". Я знаю что сейчас это правило имеет множество исключению (например sidecar паттерн), но для этого конкретного случая я предпочитаю использовать разные контейнеры для ingress и нашего приложения. Поэтому я изменил образ в директиве 'FROM' и просто удалил 'RUN apt-get update && apt-get install -y nodejs' из предоставленного Dockerfile (кстати в этой строчке еще была опечатка 'upddate').<br>
b) Далее, я раскоментировал строку 'WORKDIR /app'. Возможно это необязательный шаг, но хранить код приложения и зависимые файлы в отдельной папке лучше и прозрачнее. Как минимум это может уменьшить вероятность ошибок, например, с путями к нашему приложению.<br>
c) Я добавил 'RUN npm install' для установки зависимостей нашего приложения.<br>
d) Исправил директиву CMD ('CMD ["node", "index.js"]') на "обычную" (не shell) потому что у нас нет переменных окружения в выражении CMD или еще что то со сложным/динамическим синтаксисом. На этом с Dockerfile вроде бы все. Но если мы попытаемся собрать его, мы обнаружим следующую проблему. Так что переходим к пункту 2.<br>

2. package.json<br>
a) Если мы попытаемся собрать наше приложение (даже не используя докер, а просто на хосте с node запустив 'npm install') мы получим следующую ошибку: 'http^0.0.1 dependency'. Я использовал поиск и выяснил что пакет с именем 'http' это не http сервер (https://www.npmjs.com/package/http), так что я думаю, что очевидно что нам нужен пакет 'http-server' (https://www.npmjs.com/package/http-server) вместо http. На текущий момент последняя версия 'http-server' это '14.1.1'. Т. к. это тестовое задание я буду использовать самую свежую доступную версию 'http-server' (итоговый package.json лежит в этом репо: Ex1/part1/package.json).
Теперь образ с нашим приложением должен собираться корректно.<br>

3. index.js<br>
a) Да, я проверил, он действительно собирается корректно. Но когда я смотрю как приложение работает в моем браузере, я вижу нечитаемый текст. Мы используем русский язык в выводе приложения, так я думаю что очевидно, в первую очередь "грешить" на кодировку. Я снова использовал поиск с запросом "how to set charset for node http-server" (честно говоря, я не слишком близко знаком с JS и node), но решение нашлось легко, добавление 'charset=utf-8' в свойства 'Content-Type'в методе res.writeHead помогло. После пересборки приложения я вижу в браузере читаемую надпись на русском языке:<br>
![image](https://github.com/Slonskiy/slotegrator-test/assets/101737363/75a307dd-8ea6-4c36-b714-f92fb39b8d92)

4. Ingress<br>
Так как я решил не использовать nginx и node с кодом нашего приложения в одном контейнере, давайте решим типичную задачу развертывания ingress.<br>
Я сделаю это двумя путями - с использованием только обычного консольного docker и с использованием docker-compose.<br>
a) Docker engine.<br>
Очевидно нам нужен nginx (возможно использовать, например, haproxy  или любой другой аналогичный продукт) :) Давайте возьмем nginx:latest.<br>
Я взял очень простой конфиг для nginx (он более чем обычный, так что я не думаю что в этом месте нужны комментарии):<br>
```
events { worker_connections 1024; }

http {
    server {
        listen 80;

        location / {
            proxy_pass http://slotegrator:3000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```
Так как nginx будет использоваться только в качестве ingress-сервиса, то я предполагаю что мы не хотим что бы к нашему приложению можно было обратиться напрямую "снаружи". Для этого мы создадим в докере виртуальную сеть, и подключим к ней контейнер с нашим приложением и ingress сервис:<br>
`sudo docker network create app-network`<br>
После этого попробуем запустить контейнер с нашим приложением и наш ingress (я не буду пересобирать образ с нашим приложением, потому что он у меня уже есть и с первой части задания изменений в нем не было:<br>
`sudo docker run -d --rm --name slotegrator --network app-network slotegrator/app`<br>
`sudo docker run -d --name nginx-ingress --network app-network -p 80:80 -v $(pwd)/nginx.conf:/etc/nginx/nginx.conf:ro nginx:latest`<br>
Все должно быть хорошо, но нет - ingress завершается с ошибкой 'host not found in upstream "slotegrator"'.<br>
После небольшого времени проведенного в поиске, я понял что nginx в официальном образе с dockerhub пытается получить адресс используя оба IP (IPv6 and IPv4) протокола. Это описано на stack overflow и частично [тут](https://nginx.org/en/docs/http/ngx_http_core_module.html#resolver). Как становиться понятно из результатов поиска, docker не имеет ipv6 (или из коробки он не активен), тогда как nginx пытается получить адресс или сначала по IPv6, или обязательно по обоим протоколам. Поэтому я просто добавил следующую строчку в секцию http моего nginx config: 'resolver 127.0.0.11 ipv6=off;'. И это работает.<br>
Теперь я могу видеть тот же результат что и в первой части, но уже на 80-м порту на localhost, т. к. nginx слушает на хост машине 80-й порт и потом проксирует запрос на наше приложение.<br>
b) Docker-compose<br>
А теперь давайте сделаем тоже самое что предыдушей подчасти, но используя docker-compose.<br>
На самом деле, все что нам нужно это то что у нас уже есть (корректные Dockerfile, package.json, index.js и nginx.conf), установленный docker-compose и docker-compose.yml.<br>
Я написал простой docker-compose.yml для нашего случая:<br>
```
version: '3'

services:
  slotegrator:
    build:
      context: ./app
      dockerfile: Dockerfile
    networks:
      - app-network
  
  nginx-ingress:
    image: nginx:latest
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    networks:
      - app-network
    depends_on:
      - slotegrator

networks:
  app-network:
    driver: bridge
```
В этом случае я подразумеваю что структура файлов будет как в моем репозитарии: Dockerfile и исходники приложения в подпапке app и nginx.conf должен быть уровнем выше, там же где и docker-compose.yml.<br>
После запуска, как можно видеть на моем скрине приложение работает:
![image](https://github.com/Slonskiy/slotegrator-test/assets/101737363/23afe334-3db9-41a1-a255-a5058b059984)

Заключение:<br>
В-первой части этого упражение я выбрал использование другого базового образа Docker для нашего приложения и исправил несколько проблем с приложением и его контейнеризацией (я раскоментировал директиву 'WORKDIR', добавил шаг 'RUN npm install' и исправил директиву 'CMD' в Dockerfile. Так же я изменил зависимость для http сервера в package.json и исправил кодировку в исходнике приложения) и проверил работоспособность контейнеризированного приложения.<br>
Во-второй части я добавил ingress сервис (на nginx как отдельный контейнер), создал виртуальную сеть в докере, присоединил оба контейнера к ней и исправил проблему с разрешением адресов доменных имен в nginx для нашего случая.
Ну и наконец, я использовал docker-compose для сокращения ручного труда при деплое этого приложения.
Я не пробовал добавить образ и контейнер с certbot или использовать полученные другим образом ssl сертификаты, потому что у меня нет полноценного доменного имени и результат может быть непрозрачным. Но, конечно, добавить ssl для http возможно и это не самая сложная задача.
P. S. Корректный Dockerfile (и остальные файлы использованные при решении) лежит в двух местах этого репо:
- Ex1/part1/
- Ex1/part2/
- Ex1/part2/compose/
- Ex1/part2/compose/app


 # Exercise 2
Я буду использовать minikube на моей рабочей станции. У меня не слишком много опыта с minikube, так что большая часть сложностей возникших с этим заданием были с minikube.<br>
В начале я хочу заметить что написание манифестов не только ручная работа. Большая часть дистрибютивов kubernetes может генерировать простые манифесты самостоятельно.<br>
И в рамках этой задачи я хочу обратить внимание на [статью](https://kubernetes.io/docs/tutorials/stateful-application/mysql-wordpress-persistent-volume/) из официальной документации kubernetes где разобран описываемый случай.<br>
Но не интересно просто скопировать все оттуда, поэтому я попосил друга написать простое приложение на питоне (оно настолько простое, что я и сам мог бы, но потратил бы ощутимо больше времени) которое будет создавать файлы и хранить их на PV.<br>
1. Application<br>
Это простое веб приложение на питоне на странице которого есть только одна кнопка, при нажатии на которую приложени будет создавать файл с таймштампом в имени. Мы будем хранить эти файлы на PV и проверить что пеерсоздание POD'a приложения не влияет на хранимые файлы.<br> Исходный код приложения (так же как файл зависимостей, темплейт страницы и Dockerfile) может быть найден в этом репо: Ex2/src<br>
Давайте соберем наше приложение. С этим могут быть сложности в моем конкретном окружениии, но я всегда могу просто собрать приложение и выложить на dockerhub и прописать в манифесте брать образ с докерхаба.<br>
Для начала давайте убедимся что я нахожусь в контексте кластера minicube:<br>
`kubectl config use-context minikube`<br>
Далее, я конфигурую окружение моей CLI для использования сервиса докера миникуба:<br>
`eval $(minikube docker-env)`<br>
И соберем образ нашего приложения:<br>
`docker build -t web-test-app:latest .`<br>
Теперь образ моего приложения готов и я могу использовать его из minikube просто по имени образа в манифесте деплоя.<br>
Что бы быть уверенным что мое приложения работает как ожидается, для начала я запущу его просто в докере (пришлось собрать его еще раз в моем обычном окружении, т. к. иначе оно будет будет недоступно из браузера, из-за окружения minikube):<br>
`docker build -t web-test-app:latest .`<br>
`sudo docker run -d --rm --name web-test-app -p 16000:5000 web-test-app`<br>
Похоже приложение работает:<br>
![image](https://github.com/Slonskiy/slotegrator-test/assets/101737363/85f90598-39b2-4f89-a92e-ffcd2ab0c312)
Давайте проверим что оно создает файлы как ожидается - приложение должно присать файлы в папку /data. Конечно в образе приложения этой папки нет, поэтому я просто создам ее руками сам (я приложу скриншот для того что бы было понятнее):<br>
![image](https://github.com/Slonskiy/slotegrator-test/assets/101737363/1b4371e2-7cba-4418-b2b7-a017205a090f)
Хорошо, теперь я уверен что у меня есть веб приложение которые использует файловую систему для хранения своих данных.<br>

2. Minikube<br>
Т. к. у меня чистая инсталяция minikube, мне понадобиться включит ingress плагин:<br>
`minikube addons enable ingress`<br>
a) Deployment<br>
Я создал черновик манифеста деплоймента следующей командой:<br>
`kubectl create deployment web-test-app-deployment --image=web-test-app:latest --port=5000`<br>
Задеплоится оно не сможет, как минимум потому что мне необходимо установить 'imagePullPolicy: Never' в манифестве, что специфично для моего окружения, но я не нашел как это сделать с помощью 'kubectl create deployment'. Но данная команда сгенерила черновик деплоя который мне нужен (или я мог бы взять его из любого другого примера деплоя).<br>
Я удалил из сгенеренного манифеста большую часть записей из блока metadata, spec.template.metadata.creationTimestamp, добавил в spec.template.spec.containers 'imagePullPolicy: Never', изменил значение spec.selector.matchLabels.app на 'web-test-app' так же как значение spec.template.metadata.labels.app и удалил все после spec.template.spec.containers.ports потому что все эти записи опциональны (или наприме описывают текущее состояние объекта что в манифесте деплоя не нужно, но при желании их частично можно оставить).<br>
Так что, мой черновик сейчас выглядит вот так:<br>
```
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-test-app-deployment
spec:
  replicas: 1
  selector:
    matchLabels:
      app: web-test-app
  template:
    metadata:
      labels:
        app: web-test-app
    spec:
      containers:
      - name: web-test-app
        image: web-test-app:latest
        imagePullPolicy: Never
        ports:
        - containerPort: 5000
```
Теперь мне нужно добавить описание нашего волума в деплой и это не сложно (для того что бы сделать это я смотрел в примеры в официальной документации кубернейтеса):<br>
```
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-test-app-deployment
spec:
  replicas: 1
  selector:
    matchLabels:
      app: web-test-app
  template:
    metadata:
      labels:
        app: web-test-app
    spec:
      containers:
      - name: web-test-app
        image: web-test-app:latest
        imagePullPolicy: Never
        ports:
        - containerPort: 5000
        volumeMounts:
        - name: data-volume
          mountPath: /data
      volumes:
      - name: data-volume
        persistentVolumeClaim:
          claimName: web-test-app-pvc
```
b) PVC<br>
У меня из коробки есть только один StorageClass. Он называется 'standard' и я буду использовать его. Но раннее для организации Persistant Storage в Openshift у меня был опыт использования NFS и [SeaWeed FS](https://github.com/seaweedfs/seaweedfs).<br>
Итак, создание манифеста PersistentVolumeClaim должно быть не слишком сложным:<br>
```
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: web-test-app-pvc
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: standard
  resources:
    requests:
      storage: 1Gi
```
c) Service<br>
Черновик так же может быть сгенерирован с помощью kubectl:<br>
`kubectl expose deployment web-test-app-deployment --type=NodePort --port=80`<br>
Но в этом случае я возьму его и примеров и изменю под мое приложение:<br>
```
apiVersion: v1
kind: Service
metadata:
  name: web-test-app-service
spec:
  selector:
    app: web-test-app
  ports:
    - protocol: TCP
      port: 80
      targetPort: 5000
  type: NodePort
```
d) Ingress<br>
Честно говоря я взял его из официальной [документации](https://raw.githubusercontent.com/kubernetes/website/main/content/en/examples/service/networking/minimal-ingress.yaml).<br> 
```
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web-test-app-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  rules:
  - host: web-test-app.localkube
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web-test-app-service
            port:
              number: 80
```
3. Checking<br>
Давайте задеплоим наши сущности в minikube кластер (возможно сделать один большой yaml в котором будут все наши манифесты, но я думаю для этого упражнения будет лучше иметь раздельные файлы:<br>
![image](https://github.com/Slonskiy/slotegrator-test/assets/101737363/9f6fb562-3a5b-42c2-9f69-0a0007c20b8b)<br>
По некоторым причинам (я не хочу использовать IP адресс без имени, и я просто хочу выглядеть солидней) я добавил следующую запись в мой '/etc/hosts':<br>
`192.168.49.2 web-test-app.localkube`<br>
И после деплоя приложения я должен иметь возможность открыть мое приложение адресу имени хоста. И это действительно так:<br>
![image](https://github.com/Slonskiy/slotegrator-test/assets/101737363/2b8303d5-e2d7-4320-8c24-191c6c6fa46b)<br>
Сетификата нет, но кластер все равно слушает https схему.<br>
Теперь давайте посмотрим на persistant storage:<br>
![image](https://github.com/Slonskiy/slotegrator-test/assets/101737363/167528a9-dfe5-4a54-a1da-9e393b0c9f8d)<br>
Теперь у нас есть путь по которому должны храниться файлы которое создает наше приложение: /tmp/hostpath-provisioner/default/web-test-app-pvc<br>
Давайте соединимся с minikube по ssh и проверим что файлы действительно хранятся как ожидается:<br>
`minikube ssh`<br>
![image](https://github.com/Slonskiy/slotegrator-test/assets/101737363/3921d0e4-6a34-45c0-8258-950353fe3b8d)<br>
Отлично! Теперь осталось проверить что файлы не пропадут после пересоздания/рестата POD'а с приложением.<br>
Да, так и есть:<br>
![image](https://github.com/Slonskiy/slotegrator-test/assets/101737363/e65b1447-2ad4-463c-81ad-db1fccf64c87)<br>

Заключение:<br>
Я не могу назвать себя очень опытным пользователем кубернейтеса, но есть достаточно возможностей получить требуемые черновики/примеры манифестов или хелм чартов, так что я не думаю что деплой простого приложения в кубернейтес это слишком сложно. Конечно, кубернейтес это не только про деплой приложений. Это про масштабируемость, это про сборку образов, про etcd и много-много всего. Но я надеюсь что я завершил программу "минимум" успешно.<br>

# Exercise 3
Setup HPA for our application.<br>
Честно говоря, я раньше не делал ничего похожего, так что я просто прочел документацию ([эту](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale-walkthrough/) и [эту](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/#support-for-multiple-metrics)) и как и в предыдущих случаях драфт манифеста для HPA может быть сгенерирован с помощью kubectl.<br>
`kubectl autoscale deployment web-test-app-deployment -n default --cpu-percent=20 --min=1 --max=3`<br>
В результате у меня есть черновик для моего HPA:<br>
```
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-test-app-hpa
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-test-app-deployment
  minReplicas: 1
  maxReplicas: 3
  metrics:
  - resource:
      name: cpu
      target:
        averageUtilization: 20
        type: Utilization
    type: Resource
```
Я поменял некоторые параметры HPA для моего приложения и в итоге получил следуоющее:<br>
```
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-test-app-hpa
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-test-app-deployment
  minReplicas: 1
  maxReplicas: 3
  metrics:
  - type: ContainerResource
    containerResource:
      name: cpu
      container: web-test-app
      target:
        type: Utilization
        averageUtilization: 5
  - type: ContainerResource
    containerResource:
      name: memory
      container: web-test-app
      target:
        type: AverageValue
        averageValue: 15Mi
```
Я применил мой HPA манифест к моему Kubernetes. И теперь время проверить как он работает.<br>
Мое приложение потребляет поядка 20 мегабайт памяти и совсем чуть-чуть CPU (когда я смотрю на потребляемые ресурсы с помощью 'kubectl get hpa web-test-app-hpa --watch' для потребления CPU выводится статус '<unknown>' и небольшие числа в дашборде кластера, поэтому я считаю что мое потребление CPU моим приложением пренебрежимо мало). Я не смог быстро придумать как заставить приложение активней потреблять ресурсы потому что оно очень простое. Я пробовал создать нагрузку следующей командой 'kubectl run -i --tty load-generator --rm --image=busybox:1.28 --restart=Never -- /bin/sh -c "while sleep 0.01; do wget -q -O- http://web-test-app-service ; done"', но эта нагрузка чуть-чуть увеличивает потребление памяти POD'ом, но не сказывается существенно на потреблении CPU. Поэтому я просто установил цель по памяти для HPA (изначально было CPU 20%/RAM 30Mb) на 15 Мб. Применил новую версию манифеста и я могу что HPA работает корректно - теперь у нас три реплики:<br>
![image](https://github.com/Slonskiy/slotegrator-test/assets/101737363/c07bf866-5796-4143-819e-671fba801f85)

Заключение:<br>
Это был мой первый опыт Horizontal Pod Autoscaler, я попробовал только базовые функции (например у меня был вариант манифеста который срабатывает по сумманому потреблению подов, а не конретного контейнера), но это было не так сложно и теперь я знаю некоторые примеры как HPA может быть сконфигурирован.


