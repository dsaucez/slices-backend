## Prepare the environement

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
go get core/token
go mod download github.com/gorilla/mux
```

## Start the backend
```
go run main.go 
```