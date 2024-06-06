package api

import (
	"net/http"
)

// List all cores
// (GET /cores/)
func (Server) GetCores(w http.ResponseWriter, r *http.Request, params GetCoresParams) {
	resp := GetCores()

	returnOk(w, r, resp)
}
