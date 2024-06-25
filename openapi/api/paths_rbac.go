package api

import (
	"net/http"
	"time"
)

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
	userInfo, error := getUserInfo(r, w)
	if error {
		returnError(w, r, userInfo["error"])
		return
	}

	var token Token = userInfo["token"]
	resp := Tokenmap{
		Token: &token,
	}

	returnOk(w, r, resp)
}
