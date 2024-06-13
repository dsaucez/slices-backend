package api

import (
	"net/http"
	"runtime"
)

// (GET /healthz)
func (Server) GetHealthz(w http.ResponseWriter, r *http.Request) {
	var m runtime.MemStats
	runtime.ReadMemStats(&m)
	returnOk(w, r, m)
}
