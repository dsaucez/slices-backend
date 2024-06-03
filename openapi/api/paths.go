package api

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"time"

	"github.com/casbin/casbin"
	"github.com/google/uuid"
)

var (
	db       = make(map[string]*Core)
	enforcer *casbin.Enforcer
)

func (ctx *MiddlewareCtx) Init() {
	var err error
	enforcer, err = casbin.NewEnforcerSafe(ctx.Ctx["model"], ctx.Ctx["policy"])
	if err != nil {
		panic(err)
	}
}

// == Middleware ===============================================================
type MiddlewareCtx struct {
	Ctx map[string]any
}

func (ctx *MiddlewareCtx) AuthMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		log.Println("Authentication handler", r.Method, r.URL.Path)
		next.ServeHTTP(w, r)
	})
}

func (ctx *MiddlewareCtx) RoleMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		fmt.Println(ctx.Ctx)

		cookie, err := r.Cookie("username")
		if err != nil {
			returnGeneric(w, r, "token not defined", http.StatusBadRequest)
			return
		}
		username := cookie.Value

		// verify that the user is allowed to do this action
		authorized, err := enforcer.EnforceSafe(username, r.URL.Path, r.Method)
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

// == Helper functions =========================================================

func getRequestBody(r *http.Request) (PostCoreJSONRequestBody, bool) {
	body, err := io.ReadAll(r.Body)
	if err != nil {
		return PostCoreJSONRequestBody{}, true
	}

	var request PostCoreJSONRequestBody
	err = json.Unmarshal(body, &request)
	if err != nil {
		return PostCoreJSONRequestBody{}, true
	}

	return request, false
}

func returnGeneric(w http.ResponseWriter, r *http.Request, resp any, statusCode int) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)
	_ = json.NewEncoder(w).Encode(resp)
}

func returnCreated(w http.ResponseWriter, r *http.Request, resp any) {
	returnGeneric(w, r, resp, http.StatusCreated)
}

func returnOk(w http.ResponseWriter, r *http.Request, resp any) {
	returnGeneric(w, r, resp, http.StatusOK)
}

func returnNotFound(w http.ResponseWriter, r *http.Request, resp any) {
	returnGeneric(w, r, resp, http.StatusNotFound)
}

func returnError(w http.ResponseWriter, r *http.Request, errormsg string) {
	returnGeneric(w, r, Error{Error: &errormsg}, http.StatusInternalServerError)
}

// == Core functions ===========================================================
type CoreErrorCode int

const (
	OK CoreErrorCode = iota
	NOTFOUND
	INVALIDSTATE
)

func createCore(core_params CoreParams) Core {
	var id Uuid = uuid.New().String()
	var state CoreState = Created
	nfs := new(NetworkFunctions)

	core := Core{
		NetworkFunctions: nfs,
		Parameters:       &core_params,
		Uuid:             &id,
		State:            &state,
	}

	db[id] = &core
	return core
}

func deployCore(id string) {
	fmt.Println("should deploy the core ", id)
	core := db[id]

	var state CoreState = Deployed
	core.State = &state
}

func stopCore(id string) {
	fmt.Println("should stop the core ", id)
	core := db[id]

	var state CoreState = Stopped
	core.State = &state
}

func deleteCore(id string) (CoreErrorCode, string) {
	core := db[id]

	// sanity checks
	if core == nil {
		msg := fmt.Sprintf("core %s does not exist", id)
		return NOTFOUND, msg
	}
	if *core.State != Stopped {
		msg := fmt.Sprintf("trying to delete core %s that is not stopped", id)
		return INVALIDSTATE, msg
	}

	delete(db, id)

	return OK, fmt.Sprintf("core %s deleted", id)
}

// == Paths ====================================================================

// (POST /core/)
func (Server) PostCore(w http.ResponseWriter, r *http.Request, params PostCoreParams) {
	// retriere info
	core_params, err := getRequestBody(r)
	if err {
		returnError(w, r, "Failed to read Request")
		return
	}

	// Create the core
	core := createCore(core_params)

	returnCreated(w, r, core)
}

// Delete the core configuration
// (DELETE /core/{id})
func (Server) DeleteCoreId(w http.ResponseWriter, r *http.Request, id Uuid, params DeleteCoreIdParams) {
	core := db[id]

	code, msg := deleteCore(id)

	// sanity checks
	switch code {
	case NOTFOUND:
		log.Println(msg)
		returnNotFound(w, r, Empty{})
		return
	case INVALIDSTATE:
		log.Println(msg)
		returnError(w, r, msg)
		return
	default:
		returnOk(w, r, core)
		return
	}
}

// Get core configuration
// (GET /core/{id})
func (Server) GetCoreId(w http.ResponseWriter, r *http.Request, id Uuid, params GetCoreIdParams) {
	core := db[id]

	if core == nil {
		log.Printf("core %s does not exist\n", id)
		returnNotFound(w, r, Empty{})
		return
	}
	if params.Action != nil {
		if *params.Action == Deploy {
			var state CoreState = Deploying
			core.State = &state

			deployCore(id)
		}
		if *params.Action == Stop {

			var state CoreState = Stopping
			core.State = &state

			stopCore(id)
		}
	}

	returnOk(w, r, core)
}

// Add a UE to the database
// (POST /core/{id}/UE)
func (Server) PostCoreIdUE(w http.ResponseWriter, r *http.Request, id Uuid, params PostCoreIdUEParams) {
}

// Get UE information
// (GET /core/{id}/UE/{imsi})
func (Server) GetCoreIdUEImsi(w http.ResponseWriter, r *http.Request, id Uuid, imsi Imsi, params GetCoreIdUEImsiParams) {
}

// Add a UE to the database
// (POST /core/{id}/UPF)
func (Server) PostCoreIdUPF(w http.ResponseWriter, r *http.Request, id Uuid, params PostCoreIdUPFParams) {
}

// List all cores
// (GET /cores/)
func (Server) GetCores(w http.ResponseWriter, r *http.Request, params GetCoresParams) {
	resp := db

	returnOk(w, r, resp)
}

// Logout the user
// (GET /logout)
func (Server) GetLogout(w http.ResponseWriter, r *http.Request, params GetLogoutParams) {
	resp := Empty{}

	http.SetCookie(w, &http.Cookie{
		Name:     "token",
		Value:    "",
		HttpOnly: true,
		Secure:   false,
		MaxAge:   0,
		Expires:  time.Unix(0, 0),
	})

	returnOk(w, r, resp)
}

// Generate and return an JWT API token
// (GET /token)
func (Server) GetToken(w http.ResponseWriter, r *http.Request) {

	var token Token = "12345"

	http.SetCookie(w, &http.Cookie{
		Name:     "token",
		Value:    token,
		HttpOnly: true,
		Secure:   true,
	})

	resp := Tokenmap{
		Token: &token,
	}

	returnOk(w, r, resp)
}
