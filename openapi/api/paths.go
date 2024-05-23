package api

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"time"

	"github.com/google/uuid"
)

var (
	db = make(map[string]*Core)
)

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

// == Paths ====================================================================

// (POST /core/)
func (Server) PostCore(w http.ResponseWriter, r *http.Request, params PostCoreParams) {
	// Create the core
	// ..TODO

	// retriere info
	core_params, err := getRequestBody(r)

	if err {
		returnError(w, r, "Failed to read Request")
		return
	}
	var id Uuid = uuid.New().String()
	state := new(CoreState)
	nfs := new(NetworkFunctions)

	core := Core{
		NetworkFunctions: nfs,
		Parameters:       &core_params,
		Uuid:             &id,
		State:            state,
	}

	db[id] = &core

	returnCreated(w, r, core)
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
		if *params.Action == "deploy" {
			fmt.Println("should deploy the core ", id)
			var state CoreState = Deploying
			core.State = &state

			returnOk(w, r, core)
			return
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
