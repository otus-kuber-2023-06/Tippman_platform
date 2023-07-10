FROM nginx:latest

RUN mkdir /app
RUN usermod -u 1001 nginx && groupmod -g 1001 nginx
ADD nginx.conf /etc/nginx/nginx.conf
EXPOSE 8000
ENTRYPOINT ["nginx", "-g", "daemon off;"]