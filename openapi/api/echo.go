package api

import (
	"encoding/json"
	"net/http"
	"time"
)

// (GET /logout)
func (Server) GetLogout(w http.ResponseWriter, r *http.Request) {
	resp := Empty{}

	http.SetCookie(w, &http.Cookie{
		Name:     "token",
		Value:    "",
		HttpOnly: true,
		Secure:   false,
		MaxAge:   0,
		Expires:  time.Unix(0, 0),
	})

	w.WriteHeader(http.StatusOK)
	_ = json.NewEncoder(w).Encode(resp)
}

// (GET /token)
func (Server) GetToken(w http.ResponseWriter, r *http.Request) {
	resp := Token{
		Token: "coucou",
	}

	w.WriteHeader(http.StatusOK)
	_ = json.NewEncoder(w).Encode(resp)
}
