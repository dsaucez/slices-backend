package api

import (
	"fmt"
	"net/http"
)

// List all cores
// (GET /cores/)
func (Server) GetCores(w http.ResponseWriter, r *http.Request, params GetCoresParams) {
	resp := GetCores()

	userInfo, _ := getUserInfo(r, w)
	fmt.Println(userInfo)
	returnOk(w, r, resp)
}
