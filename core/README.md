## Local dev environment (useful for development)

### Set environement variables
`CLIENT_ID` and `CLIENT_SECRET`correspond to the credentials for the service
registered on the SLICES-SC portal (i.e., client ID and client secret,
respectively).

`REDIRECT_URI` is the redirection URL registered on the SLICES-SC portal (e.g.,
http://localhost:8008/redirect-call).

`TOKEN_URL` and `OAUTH_URL` are the URL for token generation (e.g.,
https://portal.slices-sc.eu/oauth/token) and OAUTH authorization (e.g.,
https://portal.slices-sc.eu/oauth/authorize)

### Get Dependencies
```
 go get -d -v .
```

### Start the backend
```
go run main.go 
```

## Docker environement

Build the image

 ```
 docker build -t slices-backend -f Dockerfile .
 ```

 Define environment variables mentionned above in an variable list (e.g.,
 `env.list`) then run the 

 ```
 docker run --env-file env.list --rm -d -p 8008:8008  slices-backend
 ```

