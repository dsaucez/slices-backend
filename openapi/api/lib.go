package api

import (
	"encoding/json"
	"io"

	"net/http"
	"strings"
)

// == Helper functions =========================================================

func getUserInfo(r *http.Request, w http.ResponseWriter) (map[string]string, bool) {
	userInfo := map[string]string{
		"email":          strings.ToLower(r.Header["Oidc_claim_email"][0]),
		"last_name":      r.Header["Oidc_claim_last_name"][0],
		"first_name":     r.Header["Oidc_claim_first_name"][0],
		"organization":   r.Header["Oidc_claim_organization"][0],
		"username":       r.Header["Oidc_claim_username"][0],
		"public_ssh_key": r.Header["Oidc_claim_public_ssh_key"][0],
		"token":          r.Header["Oidc_access_token"][0]}

	return userInfo, false
}

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
