package api

import (
	"encoding/base64"
	"net/http"
	"net/url"
	tok "openapi/token"
	"os"

	"github.com/casbin/casbin"
)

var (
	enforcer   *casbin.Enforcer
	rbacModel  = os.Getenv("RBAC_MODEL")
	rbacPolicy = os.Getenv("RBAC_POLICY")
)

func setDefaults() {
	if len(rbacPolicy) == 0 {
		rbacPolicy = "./policy.csv"
	}

	if len(rbacModel) == 0 {
		rbacModel = "./model.conf"
	}
}

func init() {
	setDefaults()

	var err error
	enforcer, err = casbin.NewEnforcerSafe(rbacModel, rbacPolicy)
	if err != nil {
		panic(err)
	}
}

func skipMiddleware(w http.ResponseWriter, r *http.Request) bool {
	toIgnore := map[string]bool{
		"/authentication": true,
		"/redirect-call":  true,
		"/logout":         true,
		"/healthz":        true,
	}
	_, found := toIgnore[r.URL.Path]

	return found
}

func AuthMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if skipMiddleware(w, r) {
			next.ServeHTTP(w, r)
			return
		}

		tokenCookie, err := r.Cookie("token")
		var tokenValue string
		if err == nil {
			tokenValue = tokenCookie.Value
		}
		c, e := tok.VerifyToken(tokenValue)

		if err != nil || c != tok.OK {
			// if err != nil || tok.VerifyToken(tokenCookie.Value) > 0 {

			if c == tok.GENERATION_ERROR {
				returnError(w, r, e.Error())
				return
			}

			// Redirect the user to the authentication endpoint if not authenticated.
			queryParams := url.Values{}
			requestedURI := base64.StdEncoding.EncodeToString([]byte(r.RequestURI))
			queryParams.Add("requested_uri", requestedURI)

			newURI := url.URL{
				Path:     "/authentication",
				RawQuery: queryParams.Encode(),
			}

			http.Redirect(w, r, newURI.RequestURI(), http.StatusFound)
			return
		}
		// Call the next handler if the user is authenticated.
		next.ServeHTTP(w, r)

	})
}

func RoleMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if skipMiddleware(w, r) {
			next.ServeHTTP(w, r)
			return
		}

		// Extract infos from token
		tokenInfo, error := getTokenInfo(r, w)
		if error {
			returnError(w, r, tokenInfo["error"])
			return
		}

		// verify that the user is allowed to do this action
		authorized, err := enforcer.EnforceSafe(tokenInfo["username"], r.URL.Path, r.Method)
		if err != nil {
			returnError(w, r, "Could not enforce")
			return
		}
		if !authorized {
			returnGeneric(w, r, "access denied", http.StatusForbidden)
			return
		}

		next.ServeHTTP(w, r)
	})
}
