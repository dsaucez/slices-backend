package api

import (
	"encoding/json"
	"net/http"
	"time"

	"github.com/google/uuid"
)

func returnOk(w http.ResponseWriter, r *http.Request, resp any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	_ = json.NewEncoder(w).Encode(resp)

}

// (POST /core/)
func (Server) PostCore(w http.ResponseWriter, r *http.Request, params PostCoreParams) {
	var id Uuid = uuid.New().String() // generate a UUID

	// Create the core
	// ..TODO

	// return info
	resp := Core{
		NetworkFunctions: nil,
		Parameters:       nil,
		Uuid:             &id,
	}

	returnOk(w, r, resp)
}

// Get core configuration
// (GET /core/{id})
func (Server) GetCoreId(w http.ResponseWriter, r *http.Request, id Uuid, params GetCoreIdParams) {
	resp := Core{
		NetworkFunctions: nil,
		Parameters:       nil,
		Uuid:             &id,
	}

	returnOk(w, r, resp)
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
	var token Token = "1234"

	resp := Tokenmap{
		Token: &token,
	}

	returnOk(w, r, resp)
}
