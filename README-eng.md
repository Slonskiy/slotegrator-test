# Exercise 1

1. Dockerfile<br>
a) We are trying to build a JS application, and we have a 'package.json' beside the application source code. So, I assume that we should use a node-based docker image instead of nginx. For example, I'll take the latest version of the node docker image and use it. It's possible to just install node into an nginx base image, but I think it's not a good idea because of security reasons for example. If we want nginx as ingress, we'd better use another container. Also, Docker philosophy is 'one process - one container'. I know there are many exceptions (like the sidecar pattern), but in this case, I prefer to use separate ingress and application containers. So, I just removed the string 'RUN apt-get update && apt-get install -y nodejs' from our Dockerfile (there was a typo BTW).<br>
b) Next, I uncommented 'WORKDIR /app'. It's possibly an optional step, but storing the application with all dependent files in one specific folder is clearer and can reduce the possibility of errors, for example with paths.<br>
c) I added 'RUN npm install' to the Dockerfile to install our application's dependencies.<br>
d) Fixed CMD form ('CMD ["node", "index.js"]') to classic (not shell) because we have no ENV vars in CMD statement or something like pipelines, etc. It looks like that's all with the Dockerfile. But if we try to build it, we will encounter a new error. So, going to point 2.<br>

2. package.json<br>
a) a) If we try to build (not even in docker, just 'npm install') our application we will encounter an error about 'http^0.0.1 dependency'. I googled a little, and the package named 'http' is not an HTTP server (https://www.npmjs.com/package/http), so I think it's obvious that we need 'http-server' (https://www.npmjs.com/package/http-server) instead of 'http'. As I can see, the latest version of 'http-server' is '14.1.1'. As it's a test task, I will use the latest version available. (Changes are made to the package.json file: "http-server": "^14.1.1").<br>
Now, the image with our application will be built successfully.<br>
3. index.js<br>
a) Yep, as I checked, it builds successfully. But when I see how it's working in my browser, I see unreadable text. We have Russian text, and obviously, this problem is related to charset. I googled the question 'how to set charset for node http-server' (I'm not too familiar with node, actually) and added 'charset=utf-8' to the 'Content-Type' properties in the res.writeHead method. After rebuilding the application, now I see the correct text:<br>
![image](https://github.com/Slonskiy/slotegrator-test/assets/101737363/75a307dd-8ea6-4c36-b714-f92fb39b8d92)

4. Ingress<br>
As I decided to not to use nginx and none with our code in one container, let's solve common ingress task.<br>
I will do it by two ways, with using a clear docker CLI and docker-compose.<br>
a) Docker engine.<br>
Obviously, we need nginx :) Let's take nginx:latest.<br>
I created a simple config for nginx (it's a pretty typical, so I don't think that any comments needed):<br>
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
As nginx will be just ingress service, and we don't want to have access to our application from outside, we will create docker virtual net and attach application container and ingres service to it:<br>
`sudo docker network create app-network`<br>
After that will try to run container with our application and our ingress (I will not rebuid our application image this time, because I have it already and image has no changes from first part):<br>
`sudo docker run -d --rm --name slotegrator --network app-network slotegrator/app`<br>
`sudo docker run -d --name nginx-ingress --network app-network -p 80:80 -v $(pwd)/nginx.conf:/etc/nginx/nginx.conf:ro nginx:latest`<br>
All should be good, but not - ingress will fail with 'host not found in upstream "slotegrator"'.<br>
After some time with google, I understand that nginx in official image trying to solve address using both IP (IPv6 and IPv4) protocols. It's described on stackowerflow and partly [here](https://nginx.org/en/docs/http/ngx_http_core_module.html#resolver). So, I just tryied to add the follow string to the http section of my nginx config: 'resolver 127.0.0.11 ipv6=off;'. And it's works.<br>
Now I can see the same result like at first part, but on 80-th port on my localhost.<br>
b) Docker-compose<br>
Let's do the same as at previous subpart but with using docker-compose.<br>
Actually, we need just docker-compose installed and docker-compose.yml.<br>
I wrote a simple docker-compose.yml for this case:<br>
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
In this case, I assume that files structure will be like in my repo: Dockerfile and application source are in app subfolder and correct nginx.conf should be one level higher, near docker-compose.yml.<br>
As you can see on screenshot, it's working (but now, as it should be our request going to ingress on 80-th tcp port and after it nginx proxing it to our application):
![image](https://github.com/Slonskiy/slotegrator-test/assets/101737363/23afe334-3db9-41a1-a255-a5058b059984)

Conclusion:<br>
In first part of this exercise I choosed to use another base docker image and solved some problems with app (like uncommenting 'WORKDIR' statement, added 'RUN npm install' step, and corrected 'CMD' statement in the Dockerfile. Also I changed http-server dependency in the package.json and fixed encoding in the index.js) and checked that now our application is working.<br>
In second part I added ingress service (separated nginx container), created a docker virtual network, atached both containers to it, and fixed problem with names resolving in the docker virtaul net.
As last point, I used docker-compose to reduce manual work a little bit.<br>
I didn't tryied to add certbot image/container or use other ssl certificates, because I have no correct domain name, so result can be not clear. But, of course, it's possible and not too hard.<br>
P. S. Te correct Dockerfile (and other files used in this task) are in the this repo by follow paths:
- Ex1/part1/
- Ex1/part2/
- Ex1/part2/compose/
- Ex1/part2/compose/app/

 # Exercise 2
I'm starting with new minikube local installation. I'm not too expirienced with minikube speciefic, so got problems mostly with minikube.<br>
At first I would like to say, that making deploy manifests not only manual job. Most kubernetes distribs can generate minimalistic manifests by itself (like minikube, kube-spray, opensift, etc).<br>
And, there is a great articale about deploying statefull application into kubernetes from official [documentation](https://kubernetes.io/docs/tutorials/stateful-application/mysql-wordpress-persistent-volume/).<br>
But it's not interesting to copy all from there, so I asked my friend to made a simple python web application that will create some files and store them on a PV.<br>
1. Application<br>
This is simple python web application that have only one button and when it being pressed the application will create a file with time stamp name. We will store it on PV and will check that recreating application POD not affects to stored data.<br>
The application source code (as good as dependency file, web page template and Dockerfile) can be viewied in this repo: Ex2/src<br>
Let's build our application. It's can be tricky on my environment, but anyway I can just push it to dockerhub and set container path at the deploy manifest.<br>
First, ensure you're in the context of your Minikube cluster:<br>
`kubectl config use-context minikube`<br>
Next, configure my shell to use Minikube's Docker daemon:<br>
`eval $(minikube docker-env)`<br>
And build our application image:<br>
`docker build -t web-test-app:latest .`<br>
Now, my application image is ready and I can use it from minikube just by image name in deploy manifest.<br>
To be sure that my application working as expected, at first I will run it just in Docker (I need to build it one more time, because if it build in minikube docker env I can't reach it via browser):<br>
`docker build -t web-test-app:latest .`<br>
`sudo docker run -d --rm --name web-test-app -p 16000:5000 web-test-app`<br>
Looks like it working:<br>
![image](https://github.com/Slonskiy/slotegrator-test/assets/101737363/85f90598-39b2-4f89-a92e-ffcd2ab0c312)
Let's check that it creates files as expected - it should write files to the /data path. Of course in docker we have no this path so we need to create it (I will attach a screenshot to be more clear):<br>
![image](https://github.com/Slonskiy/slotegrator-test/assets/101737363/1b4371e2-7cba-4418-b2b7-a017205a090f)
Ok, now I'm sure that I have a web application that uses filesystem to store data.<br>

2. Minikube<br>
While I have clean install of minikube I need to enable ingress plugin:<br>
`minikube addons enable ingress`<br>
a) Deployment<br>
I created a draft of deployment manifest by follow command:<br>
`kubectl create deployment web-test-app-deployment --image=web-test-app:latest --port=5000`<br>
It will not work as minimum because I need to set 'imagePullPolicy: Never' due my environment, but I don't found the way how to do it with 'kubectl create deployment'. But it generated a draft that I needed (of I can just take it from any other deployment example).<br>
I have deleted from the generated manifest most of KV in the metadata stanza, spec.template.metadata.creationTimestamp, added to spec.template.spec.containers 'imagePullPolicy: Never', changed spec.selector.matchLabels.app to 'web-test-app' as well as spec.template.metadata.labels.app and removed all after spec.template.spec.containers.ports because all generated parameters are optional (we can keep them if we wish).<br>
So, my draft in correct moment looks like:<br>
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
Now I just need to add our volume to deployment and it's ready (to do that I just was looking examples in official kubernetes documentation):<br>
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
I have only one StorageClass out from the box. It called 'standard' and I will use it. But I also used NFS and [SeaWeed FS](https://github.com/seaweedfs/seaweedfs) for storing persistand data in Openshift.<br>
So, create PersistentVolumeClaim manifest will be not too difficult:<br>
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
The draft also can be generated by kubectl:<br>
`kubectl expose deployment web-test-app-deployment --type=NodePort --port=80`<br>
But in this case I will take it from examples and modify for my application:
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
Actually, I also get it from official [documentation](https://raw.githubusercontent.com/kubernetes/website/main/content/en/examples/service/networking/minimal-ingress.yaml
).<br> 
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
Let's deploy our entityes to the kube cluster (it's possible to make one big .yaml with all this stuff, but I think for this exercise will be better to have separated files):<br>
![image](https://github.com/Slonskiy/slotegrator-test/assets/101737363/9f6fb562-3a5b-42c2-9f69-0a0007c20b8b)<br>
For some reasons (don't want to use IP without name, and would like to look smarter) I added follow record to my '/etc/hosts' file:<br>
`192.168.49.2 web-test-app.localkube`<br>
And after deploynd I should can open our application by hostname. It's so:<br>
![image](https://github.com/Slonskiy/slotegrator-test/assets/101737363/2b8303d5-e2d7-4320-8c24-191c6c6fa46b)<br>
There are no certificate, but cluster listen https scheme too anyway.<br>
Now, let's look to persistant storage:<br>
![image](https://github.com/Slonskiy/slotegrator-test/assets/101737363/167528a9-dfe5-4a54-a1da-9e393b0c9f8d)<br>
Now we have path where our files should stored persistantly: /tmp/hostpath-provisioner/default/web-test-app-pvc<br>
Let's connect to minikube via ssh and check that files are stored as expected:<br>
`minikube ssh`<br>
![image](https://github.com/Slonskiy/slotegrator-test/assets/101737363/3921d0e4-6a34-45c0-8258-950353fe3b8d)<br>
Great! The last one thing that we need to check that files will not deleted after POD restart/recreate.<br>
And, yes, it works:<br>
![image](https://github.com/Slonskiy/slotegrator-test/assets/101737363/e65b1447-2ad4-463c-81ad-db1fccf64c87)<br>

Conclusion:<br>
I can't say that I'm such expirienced Kubernetes user, but there are many possibilities to get required manifests of drafts for the helm charts, so I don't think that deploying of simple application to the kubernetes is too hard. Of course, Kubernetes not only about deploying applications. It's about scalability, it's about building images, it's about etcd and many-many more. But I hope, that I finished a program 'minimum' successfully. 


