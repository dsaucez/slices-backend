package api

import (
	"fmt"
	"log"
	"net/http"
)

// (POST /core/)
func (Server) PostCore(w http.ResponseWriter, r *http.Request, params PostCoreParams) {
	// retriere info
	core_params, err := getRequestBody(r)
	if err {
		returnError(w, r, "Failed to read Request")
		return
	}

	// Create the core
	core := CreateCore(&core_params)

	returnCreated(w, r, core)
}

// Delete the core configuration
// (DELETE /core/{id})
func (Server) DeleteCoreId(w http.ResponseWriter, r *http.Request, id Uuid, params DeleteCoreIdParams) {
	code := DeleteCore(id)

	// sanity checks
	switch code {
	case CORE_NOTFOUND:
		msg := fmt.Sprintf("core %s does not exist", id)
		log.Println(msg)
		returnNotFound(w, r, Empty{})
		return
	case CORE_INVALIDSTATE:
		msg := fmt.Sprintf("trying to delete core %s that is not stopped", id)
		log.Println(msg)
		returnError(w, r, msg)
		return
	default:
		returnOk(w, r, Empty{})
		return
	}
}

// Get core configuration
// (GET /core/{id})
func (Server) GetCoreId(w http.ResponseWriter, r *http.Request, id Uuid, params GetCoreIdParams) {
	core := GetCore(id)

	if core == nil {
		log.Printf("core %s does not exist!\n", id)
		returnNotFound(w, r, Empty{})
		return
	}
	if params.Action != nil {
		if *params.Action == Deploy {
			core = DeployCore(id)
		}
		if *params.Action == Stop {
			core = StopCore(id)

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
