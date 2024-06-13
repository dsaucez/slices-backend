package token

import (
	"context"
	"fmt"
	"log"
	"os"
	"time"

	"github.com/MicahParks/keyfunc"
	"github.com/golang-jwt/jwt/v4"
)

var (
	jwksURI string
	algos   []string
)

func init() {
	jwksURI = os.Getenv("JWKS_URI")
	algos = []string{"RS512", "ES256"}
}

type ErrorCode int

const (
	OK ErrorCode = iota
	GENERATION_ERROR
	TOKEN_EXPIRED
	PARSE_ERROR
	INVALID_TOKEN
)

func VerifyToken(token string) (ErrorCode, error) {
	// TODO: DSA: handle better errors
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
		e := fmt.Errorf("failed to create JWKS from resource at the given URL")
		log.Printf("%s: %s\n", e.Error(), err.Error())
		return GENERATION_ERROR, e
	}

	// Get a JWT to parse. This is the access token sent from the OIDC server in exchange to access code.
	// Parse the JWT.
	tok, err := jwt.Parse(token, jwks.Keyfunc, jwt.WithValidMethods(algos))
	if err != nil {
		if ve, ok := err.(*jwt.ValidationError); ok && ve.Errors == jwt.ValidationErrorExpired {
			e := fmt.Errorf("the token is expired")
			return TOKEN_EXPIRED, e
		}
		e := fmt.Errorf("failed to parse the JWT %s", err.Error())
		return PARSE_ERROR, e
	}
	// Check if the token is valid based on the JWKS object.
	if !tok.Valid {
		e := fmt.Errorf("the token is not valid") // Either malformed or failed signature validation
		return INVALID_TOKEN, e

	}

	return OK, nil
}

// func CheckTokenExpiry(tokenExpiryCh chan<- bool, expiration time.Time) {
// 	// Create a ticker to check the token expiration every 5 minutes.
// 	ticker := time.NewTicker(5 * time.Minute)
// 	defer ticker.Stop()

// 	for {
// 		select {
// 		case <-ticker.C:
// 			// Check the remaining time until the token expires.
// 			remainingTime := time.Until(expiration)

// 			// If the remaining time is less than or equal to 10 minutes (600 seconds),
// 			// send a notification to the main goroutine.
// 			if remainingTime <= 10*time.Minute {
// 				tokenExpiryCh <- true
// 				return
// 			}
// 		}
// 	}
// }
