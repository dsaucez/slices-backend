package api

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	tok "openapi/token"
	"os"
	"strings"
	"time"
)

var (
	redirectURI  = os.Getenv("REDIRECT_URI")
	tokenURL     = os.Getenv("TOKEN_URL")
	oauthURL     = os.Getenv("OAUTH_URL")
	clientId     = os.Getenv("CLIENT_ID")
	clientSecret = os.Getenv("CLIENT_SECRET")
)

var LocalToken struct {
	AccessToken  string `json:"access_token"`
	ExpiresIn    int    `json:"expires_in"`
	IDToken      string `json:"id_token"`
	RefreshToken string `json:"refresh_token"`
	Scope        string `json:"scope"`
	TokenType    string `json:"token_type"`
}

// (GET /authentication)
func (Server) GetAuthentication(w http.ResponseWriter, r *http.Request, params GetAuthenticationParams) {
	requestedURI := r.URL.Query().Get("requested_uri")
	redirectURL := fmt.Sprintf("%s?client_id=%s&redirect_uri=%s&scope=openid userinfo&response_type=code&state=%s",
		oauthURL, clientId, redirectURI, requestedURI)
	http.Redirect(w, r, redirectURL, http.StatusFound)
}

// (GET /redirect-call)
func (Server) GetRedirectCall(w http.ResponseWriter, r *http.Request, params GetRedirectCallParams) {
	// Extract the authorization code from the query parameters
	code := r.URL.Query().Get("code")
	if code == "" {
		returnError(w, r, "Authorization code is missing")
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
		returnError(w, r, "Failed to exchange code for tokens")
		return
	}

	defer resp.Body.Close()

	// Read the response body
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		returnError(w, r, "Failed to read response body")
		return
	}

	// Check if the response contains an error
	var errResponse struct {
		Error string `json:"error"`
	}

	if err := json.Unmarshal(body, &errResponse); err == nil && errResponse.Error != "" {
		returnError(w, r, "Token exchange error: "+errResponse.Error)
		return
	}

	err = json.Unmarshal(body, &LocalToken)
	if err != nil {
		returnError(w, r, "Failed to parse token response")
		return
	}

	if !tok.VerifyToken(LocalToken.IDToken) {
		returnError(w, r, "Token is not valid after JWKS verification.")
		return
	}

	// Redirect the user to the desired page after successful authentication
	// Retrieve state to get initial requested URI
	state := r.URL.Query().Get("state")
	bytes, err := base64.StdEncoding.DecodeString(state)
	if err != nil {
		returnError(w, r, "requested URI missing")
		return
	}
	requestedURI := string(bytes)

	// Store the access token and other relevant information as needed in a cookie to track user authentication for later use
	http.SetCookie(w, &http.Cookie{
		Name:     "token",
		Value:    LocalToken.IDToken,
		HttpOnly: true,
		Secure:   true,
	})

	http.Redirect(w, r, requestedURI, http.StatusFound)
}

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
	tokenInfo, error := getTokenInfo(r, w)
	if error {
		returnError(w, r, tokenInfo["error"])
		return
	}

	var token Token = tokenInfo["token"]
	resp := Tokenmap{
		Token: &token,
	}

	returnOk(w, r, resp)
}
