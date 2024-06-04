package api

import "net/http"

// List all cores
// (GET /cores/)
func (Server) GetCores(w http.ResponseWriter, r *http.Request, params GetCoresParams) {
	resp := getCoresDb()

	returnOk(w, r, resp)
}
