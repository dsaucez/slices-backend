# SLICES backend

## Generate code from API specifications
```bash
oapi-codegen  --config=api/cfg.yaml api/api.yaml
```
## implement the API

...

## Environement variables

`CLIENT_ID` and `CLIENT_SECRET`correspond to the credentials for the service
registered on the SLICES-SC portal (i.e., client ID and client secret,
respectively).

`REDIRECT_URI` is the redirection URL registered on the SLICES-SC portal (e.g.,
http://localhost:8008/redirect-call).

`TOKEN_URL` and `OAUTH_URL` are the URL for token generation (e.g.,
https://portal.slices-sc.eu/oauth/token) and OAUTH authorization (e.g.,
https://portal.slices-sc.eu/oauth/authorize)

`BASE_PATH` is the basepath used as a prefix to all API andpoints (e.g., `/v1`)

`PORT` is the port on which the backends listens. Default to `8008` if not defined.

`DB_PATH` the location of the database. Default to `./db.db` if not defined.

`RBAC_MODEL` casbin RBAC model. Default to `./model.conf` if not defined.
`RBAC_POLICY` casbin RBAC policy. Defaults ot `./policy.csv` if not defined.

`JWKS_URI` source of JWKS knowledge (e.g., `https://portal.slices-sc.eu/.well-known/jwks.json`).

`PROVIDER_METADATA_URL` OIDC provider metadata (e.g., https://portal.slices-sc.eu/.well-known/openid-configuration)

`SCOPE` OIDC scope to retrieve  (e.g., "openid userinfo")

`BACKEND_URL` backend URI covered by the (reverse) proxy (e.g., http://192.0.2.1:8888/)

## Start the backend

To decouple the API implementation and the authentication we use a reverse proxy.
The proxy is in charge of dealing with OIDC and it hides the actual server from the public.

Clients access the proxy, not the actual server.

### Start the proxy

Build the image

```bash
docker build -t slices-backend-proxy proxy/
```

start the proxy

```bash
docker run -dit --name slices-backend-proxy-instance --env-file env.list -p 8008:80 -v "$PWD/proxy":/usr/local/apache2/htdocs/ -v "$PWD/proxy/conf":/usr/local/apache2/conf  slices-backend-proxy
```

### Start the backend server

#### In a local development environement

```bash
go get -d -v .

find . -name "*.go" | entr -r go run main.go
```

> [!IMPORTANT]  
> Do not forget to properly set all environment variables before launching this command.

#### In a Docker container

Build the image

 ```
 docker build -t slices-backend -f Dockerfile .
 ```

 Assuming that environment variables mentionned above are defined in the
 variable list file `env.list`, then run the following command:

 ```
 docker run --env-file env.list --rm -d -p 8888:8008  slices-backend
 ```

> [!WARNING]  
> Make sure that the export server port and the IP address to which the server
> is bound is in adequation with the content of the `BACKEND_URL` environement
> variable used by the proxy.

