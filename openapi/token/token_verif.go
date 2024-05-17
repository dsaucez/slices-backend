package token

import (
	"context"
	"log"
	"time"

	"github.com/MicahParks/keyfunc"
	"github.com/golang-jwt/jwt/v4"
)

func VerifyToken(token string) bool {

	jwksURI := "https://portal.slices-sc.eu/.well-known/jwks.json"

	// Create a context that, when cancelled, ends the JWKS background refresh goroutine.
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel() // Cancel the context when the function returns

	// Create the keyfunc options. Use an error handler that logs. Refresh the JWKS when a JWT signed by an unknown KID
	// is found or at the specified interval. Rate limit these refreshes. Timeout the initial JWKS refresh request after
	// 10 seconds. This timeout is also used to create the initial context.Context for keyfunc.Get.
	options := keyfunc.Options{
		Ctx: ctx,
		RefreshErrorHandler: func(err error) {
			log.Printf("There was an error with the jwt.Keyfunc\nError: %s", err.Error())
		},
		RefreshInterval:   time.Hour,
		RefreshRateLimit:  time.Minute * 5,
		RefreshTimeout:    time.Second * 10,
		RefreshUnknownKID: true,
	}

	// Create the JWKS from the resource at the given URL.
	jwks, err := keyfunc.Get(jwksURI, options)
	if err != nil {
		log.Fatalf("Failed to create JWKS from resource at the given URL.\nError: %s", err.Error())
	}

	// Get a JWT to parse. This is the access token sent from the OIDC server in exchange to access code.
	//example: jwtB64 := "eyJhbGciOiJFUzI1NiIsImtpZCI6ImVjMSIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL2FjY291bnQuaWxhYnQuaW1lYy5iZSIsImF1ZCI6WyJ6anNjbThySkJIN2o5Nnk1c1VlVkY1c3YiXSwiaWF0IjoxNjg0ODQ1NzE2LCJleHAiOjE2ODQ4NDkzMTYsImF1dGhfdGltZSI6MTY4NDg0NTU2NCwiYXRfaGFzaCI6IkgxYlJ6ZGVpcTVTLUptTHBDYjNKRnciLCJzdWIiOiJrY2hpYm91YkBpbnJpYS5mciIsInVzZXJuYW1lIjoia2NoaWJvdWIiLCJ1cm4iOiJ1cm46cHVibGljaWQ6SUROK2lsYWJ0LmltZWMuYmUrdXNlcitrY2hpYm91YiIsInByb2plY3RfdXJucyI6W10sImVtYWlsIjoia2FvdXRhci5jaGlib3ViQGlucmlhLmZyIiwicHVibGljX3NzaF9rZXkiOiJzc2gtcnNhIEFBQUFCM056YUMxeWMyRUFBQUFEQVFBQkFBQUJBUURFcGNNdmkydlgrVFU2U2tTc3FDMHJvMnBHckMxK2laSCtqVjJid2s1MXZIRzlaVXJQeE0va1hwYnR4UnNpaVM5bzRrRU1Jd1FRbVNIWlRQbzVUdXFzak5ZcW5LTVdWeXJXZmo5ZkgxcENqNFVQSGxxL05OTVpZVUdLK2NpMFpMbjAvTk1OMzBhMHVXMlBjeFdLQXNQQms0MUp6WUFEZGFkb3M3VlBGa29KL3NGYldobkM0SnV6SmF2NUE5SUNvWlY0U2Rjc29oYjZUVWZwbnk2QUpMNEw4Y1hmYmpLTnhGVHRLeW1UeHZHeHBNRkRqQjIxelVLcjl5d3F6QUQvMFd6Sy9uL1U5ZERXeGJsaHpFTTA2OG5rY2RnM080YnY2dkd1RzhzUXl0MlFjOGhLT2Q4YTh4SCsxMFdocHUwRnNiQ3NmN25aQkFTanZsRjR4aXNRMU5hMyJ9.mNk3bI0_uIMSfMWzp1v8hM6nVH_fXi6zFQfdWkVnPLbBRvw2D0Lo04q4ON2uvGDpSU45ARYNT7IZWw33TkSVng"

	// Parse the JWT.
	tok, err := jwt.Parse(token, jwks.Keyfunc)
	if err != nil {
		if ve, ok := err.(*jwt.ValidationError); ok && ve.Errors == jwt.ValidationErrorExpired {
			log.Println("The token is expired.")
			return false
		}
		log.Printf("Failed to parse the JWT.\nError: %s", err.Error())
		return false
	}
	// Check if the token is valid based on the JWKS object.
	if !tok.Valid {
		log.Println("The token is not valid.") // Either malformed or failed signature validation
		return false
	}

	//log.Println("The token is valid.")
	return true
}

func CheckTokenExpiry(tokenExpiryCh chan<- bool, expiration time.Time) {
	// Create a ticker to check the token expiration every 5 minutes.
	ticker := time.NewTicker(5 * time.Minute)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			// Check the remaining time until the token expires.
			remainingTime := time.Until(expiration)

			// If the remaining time is less than or equal to 10 minutes (600 seconds),
			// send a notification to the main goroutine.
			if remainingTime <= 10*time.Minute {
				tokenExpiryCh <- true
				return
			}
		}
	}
}
