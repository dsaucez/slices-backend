package api

import (
	"net/http"
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
		"/logout":  true,
		"/healthz": true,
	}
	_, found := toIgnore[r.URL.Path]

	return found
}

func RoleMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if skipMiddleware(w, r) {
			next.ServeHTTP(w, r)
			return
		}

		// Extract infos from token
		userInfo, error := getUserInfo(r, w)
		if error {
			returnError(w, r, userInfo["error"])
			return
		}

		// verify that the user is allowed to do this action
		authorized, err := enforcer.EnforceSafe(userInfo["username"], r.URL.Path, r.Method)
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
