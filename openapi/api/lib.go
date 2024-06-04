package api

import (
	"encoding/json"
	"io"
	"log"
	"net/http"

	"github.com/golang-jwt/jwt"
)

// == Helper functions =========================================================

func getTokenInfo(r *http.Request, w http.ResponseWriter) (map[string]string, bool) {
	tokenCookie, err := r.Cookie("token")

	if err != nil {
		w.WriteHeader(http.StatusInternalServerError)
		return nil, true
	}

	m := make(map[string]string)
	m["token"] = tokenCookie.Value

	stoken, _, err := new(jwt.Parser).ParseUnverified(m["token"], jwt.MapClaims{})
	if err != nil {
		msg := "Failed to parse ID token"
		log.Println(msg)
		return map[string]string{"error": msg}, true
	}

	claims, ok := stoken.Claims.(jwt.MapClaims)
	if !ok {
		msg := "Failed to extract claims from ID token."
		log.Println(msg)
		return map[string]string{"error": msg}, true
	}

	username, ok := claims["username"].(string)
	if !ok {
		msg := "Username not found in the token claims."
		log.Println(msg)
		return map[string]string{"error": msg}, true
	}
	email, ok := claims["email"].(string)
	if !ok {
		msg := "email not found in the token claims."
		log.Println(msg)
		return map[string]string{"error": msg}, true
	}

	cookieInfo := map[string]string{"token": tokenCookie.Value, "email": email, "username": username}
	return cookieInfo, false
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
