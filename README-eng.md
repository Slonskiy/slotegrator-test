# Exercise 1

1. Dockerfile<br>
a) We are trying to build a JS application, and we have a 'package.json' beside the application source code. So, I assume that we should use a node-based docker image instead of nginx. For example, I'll take the latest version of the node docker image and use it. It's possible to just install node into an nginx base image, but I think it's not a good idea because of security reasons for example. If we want nginx as ingress, we'd better use another container. Also, Docker philosophy is 'one process - one container'. I know there are many exceptions (like the sidecar pattern), but in this case, I prefer to use separate ingress and application containers. So, I just removed the string 'RUN apt-get update && apt-get install -y nodejs' from our Dockerfile (there was a typo BTW).<br>
b) Next, I uncommented 'WORKDIR /app'. It's possibly an optional step, but storing the application with all dependent files in one specific folder is clearer and can reduce the possibility of errors, for example with paths. Otherwise, we need to set up node to application actual path.<br>
c) I added 'RUN npm install' to the Dockerfile to install our application's dependencies.<br>
d) Fixed CMD form ('CMD ["node", "index.js"]') to classic (not shell) because we have no ENV vars in CMD statement or something like pipelines, etc. It looks like that's all with the Dockerfile. But if we try to build it, we will encounter a new error. So, going to point 2.<br>

2. package.json
a) a) If we try to build (not even in docker, just 'npm install') our application we will encounter an error about 'http^0.0.1 dependency'. I googled a little, and the package named 'http' is not an HTTP server (https://www.npmjs.com/package/http), so I think it's obvious that we need 'http-server' (https://www.npmjs.com/package/http-server) instead of 'http'. As I can see, the latest version of 'http-server' is '14.1.1'. As it's a test task, I will use the latest version available. (Changes are made to the package.json file: "http-server": "^14.1.1").<br>
Now, the container with our application will be built successfully.<br>
3. index.js
a) Yep, as I checked, it builds successfully. But when I see how it's working in my browser, I see unreadable text. We have Russian text, and obviously, this problem is related to charset. I googled the question 'how to set charset for node http-server' (I'm not too familiar with node, actually) and added 'charset=utf-8' to the 'Content-Type' properties in the res.writeHead method. After rebuilding the application, I see the correct text.<br>
