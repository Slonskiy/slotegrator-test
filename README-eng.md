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
After some time with google, I understand that nginx in official image trying to solve address using both IP (IPv6 and IPv4) protocols. It's described on stackowerflow and partly [here](https://nginx.org/en/docs/http/ngx_http_core_module.html#resolver). So, I just tryied to add the follow string to the http section of my nging config: 'resolver 127.0.0.11 ipv6=off;'. And it's works.<br>
Now I can the same result like at first part, but on 80-th port on my localhost.<br>
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
In this case, I assume that files structure will be like in my repo: Docker file and application source are in app subfolder and correct nginx.conf should be one level higher, near docker-compose.yml.<br>
As you can see on screen, it's working (but now, as it should be our request going to ingress on 80-th tcp port and after it nginx proxing it to our application):
![image](https://github.com/Slonskiy/slotegrator-test/assets/101737363/23afe334-3db9-41a1-a255-a5058b059984)

Conclusion:<br>
In first part of this exercise I choosed to use another base docker image and solved some problems with app (like uncommenting 'WORKDIR' statement, added 'RUN npm install' step, and corrected 'CMD' statement. Also I changed http-server dependency in the package.json and fixed encoding in the index.js. And checked that now our application is working.<br>
In second part I added ingress service (separated nginx container), created a docker virtual network, atached both containers to it, and fixed problem with names resolving in the docker virtaul net.
As last point, I used docker-compose to reduce manual work a little bit.<br>
I didn't tryied to add certbot image or use other ssl certificates, because I have no correct domain name, so result can be not clear. But, of course, it's possible and not too hard.<br>

 # Exercise 2



