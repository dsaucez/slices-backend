package main

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"os"
	"strings"
	"time"

	tok "core/token"
	b64 "encoding/base64"

	mux "github.com/gorilla/mux"
)

var (
	redirectURI  = os.Getenv("REDIRECT_URI")
	tokenURL     = os.Getenv("TOKEN_URL")
	oauthURL     = os.Getenv("OAUTH_URL")
	clientId     = os.Getenv("CLIENT_ID")
	clientSecret = os.Getenv("CLIENT_SECRET")
)

var Token struct {
	AccessToken  string `json:"access_token"`
	ExpiresIn    int    `json:"expires_in"`
	IDToken      string `json:"id_token"`
	RefreshToken string `json:"refresh_token"`
	Scope        string `json:"scope"`
	TokenType    string `json:"token_type"`
}

func logout(w http.ResponseWriter, r *http.Request) {
	http.SetCookie(w, &http.Cookie{
		Name:     "token",
		Value:    "",
		HttpOnly: true,
		Secure:   false,
		MaxAge:   0,
		Expires:  time.Unix(0, 0),
	})
}
func CoreHandler(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	w.WriteHeader(http.StatusOK)
	fmt.Fprintf(w, "Core: %v\n", vars["id"])
}

func TokenHandler(w http.ResponseWriter, r *http.Request) {
	tokenCookie, err := r.Cookie("token")

	if err != nil {
		w.WriteHeader(http.StatusInternalServerError)
		return
	}

	m := make(map[string]string)
	m["token"] = tokenCookie.Value
	m["hello"] = "world"
	token, _ := json.Marshal(m)

	http.SetCookie(w, &http.Cookie{
		Name:     "token",
		Value:    "",
		HttpOnly: true,
		Secure:   false,
		MaxAge:   0,
		Expires:  time.Unix(0, 0),
	})

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(token)

}

// func catchAllHandler() http.Handler {
// 	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
// 		fmt.Fprintf(w, "This is the people handler. %s", r.URL)
// 		w.WriteHeader(http.StatusNotFound)
// 	})
// }

func authUser(w http.ResponseWriter, r *http.Request) {
	requestedURI := r.URL.Query().Get("requested_uri")
	redirectURL := fmt.Sprintf("%s?client_id=%s&redirect_uri=%s&scope=openid userinfo&response_type=code&state=%s",
		oauthURL, clientId, redirectURI, requestedURI)
	http.Redirect(w, r, redirectURL, http.StatusFound)
}

func callback(w http.ResponseWriter, r *http.Request) {
	// Extract the authorization code from the query parameters
	code := r.URL.Query().Get("code")
	if code == "" {
		http.Error(w, "Authorization code is missing", http.StatusBadRequest)
		return
	}
	// Exchange the authorization code for access tokens
	// Prepare the request body with required parameters
	data := url.Values{}
	data.Set("grant_type", "authorization_code")
	data.Set("code", code)
	data.Set("redirect_uri", redirectURI)
	data.Set("client_id", clientId)
	data.Set("client_secret", clientSecret)

	// Send a POST request to the token endpoint to exchange the code for tokens
	req, _ := http.NewRequest("POST", tokenURL, strings.NewReader(data.Encode()))
	// Set the content type header for the request
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	// Create an HTTP client
	client := &http.Client{}
	// Send the request
	resp, err := client.Do(req)
	if err != nil {
		http.Error(w, "Failed to exchange code for tokens", http.StatusInternalServerError)
		return
	}

	defer resp.Body.Close()

	// Read the response body
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		http.Error(w, "Failed to read response body", http.StatusInternalServerError)
		return
	}

	// Check if the response contains an error
	var errResponse struct {
		Error string `json:"error"`
	}

	if err := json.Unmarshal(body, &errResponse); err == nil && errResponse.Error != "" {
		http.Error(w, "Token exchange error: "+errResponse.Error, http.StatusInternalServerError)
		return
	}

	err = json.Unmarshal(body, &Token)
	if err != nil {
		http.Error(w, "Failed to parse token response", http.StatusInternalServerError)
		return
	}

	if !tok.VerifyToken(Token.IDToken) {
		http.Error(w, "Token is not valid after JWKS verification.", http.StatusInternalServerError)
		return
	} else {
		fmt.Printf("The token is valid.\n")
	}

	// Redirect the user to the desired page after successful authentication (k8s setup parallely executed)
	// Retrieve state to get initial requested URI
	state := r.URL.Query().Get("state")
	bytes, err := b64.StdEncoding.DecodeString(state)
	if err != nil {
		http.Error(w, "requested URI missing", http.StatusBadRequest)
	}
	requestedURI := string(bytes)

	// Store the access token and other relevant information as needed in a cookie to track user authentication for later use
	http.SetCookie(w, &http.Cookie{
		Name:     "token",
		Value:    Token.IDToken,
		HttpOnly: true,
		Secure:   true,
	})
	http.Redirect(w, r, requestedURI, http.StatusFound)
}

// Middleware wthat will check if the user has a valid token to access some endpoints like netbox and k8s services, if not an authentication procedure will occur
func requireAuth(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		tokenCookie, err := r.Cookie("token")
		if err != nil || !tok.VerifyToken(tokenCookie.Value) {
			// Redirect the user to the authentication endpoint if not authenticated.
			queryParams := url.Values{}
			requestedURI := b64.StdEncoding.EncodeToString([]byte(r.RequestURI))
			queryParams.Add("requested_uri", requestedURI)

			newURI := url.URL{
				Path:     "/authentication",
				RawQuery: queryParams.Encode(),
			}

			http.Redirect(w, r, newURI.RequestURI(), http.StatusFound)
			return
		}
		// Call the next handler if the user is authenticated.
		next.ServeHTTP(w, r)
	}
}

func main() {
	router := mux.NewRouter()

	router.HandleFunc("/redirect-call", callback)
	router.HandleFunc("/core/{id:[0-9]+}", requireAuth(CoreHandler))
	router.HandleFunc("/authentication", authUser).Methods("GET")
	router.HandleFunc("/token", requireAuth(TokenHandler))
	router.HandleFunc("/logout", logout)

	srv := &http.Server{
		Handler:      router,
		Addr:         ":8008",
		WriteTimeout: 15 * time.Second,
		ReadTimeout:  15 * time.Second,
	}
	log.Fatal(srv.ListenAndServe())
}
