package api

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"os"
	"strings"
	"time"

	tok "openapi/token"

	"github.com/casbin/casbin"
	"github.com/golang-jwt/jwt"
	"github.com/google/uuid"
)

var (
	db       = make(map[string]*Core)
	enforcer *casbin.Enforcer
)

func (ctx *MiddlewareCtx) Init() {
	var err error
	enforcer, err = casbin.NewEnforcerSafe(ctx.Ctx["model"], ctx.Ctx["policy"])
	if err != nil {
		panic(err)
	}
}

var (
	redirectURI  = os.Getenv("REDIRECT_URI")
	tokenURL     = os.Getenv("TOKEN_URL")
	oauthURL     = os.Getenv("OAUTH_URL")
	clientId     = os.Getenv("CLIENT_ID")
	clientSecret = os.Getenv("CLIENT_SECRET")
)

var MyToken struct {
	AccessToken  string `json:"access_token"`
	ExpiresIn    int    `json:"expires_in"`
	IDToken      string `json:"id_token"`
	RefreshToken string `json:"refresh_token"`
	Scope        string `json:"scope"`
	TokenType    string `json:"token_type"`
}

// == Middleware ===============================================================
type MiddlewareCtx struct {
	Ctx map[string]any
}

func skipMiddleware(w http.ResponseWriter, r *http.Request) bool {
	switch r.URL.Path {
	case "/authentication":
		return true
	case "/redirect-call":
		return true
	case "/logout":
		return true
	}
	return false
}

func (ctx *MiddlewareCtx) AuthMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if skipMiddleware(w, r) {
			next.ServeHTTP(w, r)
			return
		}

		tokenCookie, err := r.Cookie("token")
		if err != nil || !tok.VerifyToken(tokenCookie.Value) {
			// Redirect the user to the authentication endpoint if not authenticated.
			queryParams := url.Values{}
			requestedURI := base64.StdEncoding.EncodeToString([]byte(r.RequestURI))
			queryParams.Add("requested_uri", requestedURI)

			newURI := url.URL{
				Path:     "/authentication",
				RawQuery: queryParams.Encode(),
			}

			fmt.Println("redirection!")
			http.Redirect(w, r, newURI.RequestURI(), http.StatusFound)
			return
		}
		// Call the next handler if the user is authenticated.
		next.ServeHTTP(w, r)

	})
}

func (ctx *MiddlewareCtx) RoleMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if skipMiddleware(w, r) {
			next.ServeHTTP(w, r)
			return
		}

		fmt.Println(ctx.Ctx)

		////////////
		//
		// Parse the ID token to extract the claims (payload)
		// Access the "sub" claim from the token's claims
		// Extract the username from the claims
		cookieInfo, error := getCookieInfo(r, w)
		if error {
			returnError(w, r, cookieInfo["error"])
			return
		}
		///////////////////////

		// verify that the user is allowed to do this action
		authorized, err := enforcer.EnforceSafe(cookieInfo["username"], r.URL.Path, r.Method)
		if err != nil {
			returnError(w, r, "Could not enforce")
			return
		}
		if !authorized {
			returnGeneric(w, r, "access denied", http.StatusForbidden)
			return
		}

		next.ServeHTTP(w, r)
	})
}

func getCookieInfo(r *http.Request, w http.ResponseWriter) (map[string]string, bool) {
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
		fmt.Println(msg)
		return map[string]string{"error": msg}, true
	}

	claims, ok := stoken.Claims.(jwt.MapClaims)
	if !ok {
		msg := "Failed to extract claims from ID token."
		fmt.Println(msg)
		return map[string]string{"error": msg}, true
	}

	username, ok := claims["username"].(string)
	if !ok {
		msg := "Username not found in the token claims."
		fmt.Println(msg)
		return map[string]string{"error": msg}, true
	}
	email, ok := claims["email"].(string)
	if !ok {
		msg := "email not found in the token claims."
		fmt.Println(msg)
		return map[string]string{"error": msg}, true
	}

	cookieInfo := map[string]string{"token": tokenCookie.Value, "email": email, "username": username}
	return cookieInfo, false
}

// == Helper functions =========================================================

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

// == Core functions ===========================================================
type CoreErrorCode int

const (
	OK CoreErrorCode = iota
	NOTFOUND
	INVALIDSTATE
)

func createCore(core_params CoreParams) Core {
	var id Uuid = uuid.New().String()
	var state CoreState = Created
	nfs := new(NetworkFunctions)

	core := Core{
		NetworkFunctions: nfs,
		Parameters:       &core_params,
		Uuid:             &id,
		State:            &state,
	}

	db[id] = &core
	return core
}

func deployCore(id string) {
	fmt.Println("should deploy the core ", id)
	core := db[id]

	var state CoreState = Deployed
	core.State = &state
}

func stopCore(id string) {
	fmt.Println("should stop the core ", id)
	core := db[id]

	var state CoreState = Stopped
	core.State = &state
}

func deleteCore(id string) (CoreErrorCode, string) {
	core := db[id]

	// sanity checks
	if core == nil {
		msg := fmt.Sprintf("core %s does not exist", id)
		return NOTFOUND, msg
	}
	if *core.State != Stopped {
		msg := fmt.Sprintf("trying to delete core %s that is not stopped", id)
		return INVALIDSTATE, msg
	}

	delete(db, id)

	return OK, fmt.Sprintf("core %s deleted", id)
}

// == Paths ====================================================================

// (GET /authentication)
func (Server) GetAuthentication(w http.ResponseWriter, r *http.Request) {
	fmt.Println("coucou")

	requestedURI := r.URL.Query().Get("requested_uri")
	redirectURL := fmt.Sprintf("%s?client_id=%s&redirect_uri=%s&scope=openid userinfo&response_type=code&state=%s",
		oauthURL, clientId, redirectURI, requestedURI)
	http.Redirect(w, r, redirectURL, http.StatusFound)
}

// (GET /redirect-call)
func (Server) GetRedirectCall(w http.ResponseWriter, r *http.Request) {
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

	err = json.Unmarshal(body, &MyToken)
	if err != nil {
		http.Error(w, "Failed to parse token response", http.StatusInternalServerError)
		return
	}

	if !tok.VerifyToken(MyToken.IDToken) {
		http.Error(w, "Token is not valid after JWKS verification.", http.StatusInternalServerError)
		return
	} else {
		fmt.Printf("The token is valid.\n")
	}

	// Redirect the user to the desired page after successful authentication (k8s setup parallely executed)
	// Retrieve state to get initial requested URI
	state := r.URL.Query().Get("state")
	bytes, err := base64.StdEncoding.DecodeString(state)
	if err != nil {
		http.Error(w, "requested URI missing", http.StatusBadRequest)
	}
	requestedURI := string(bytes)

	// Store the access token and other relevant information as needed in a cookie to track user authentication for later use
	http.SetCookie(w, &http.Cookie{
		Name:     "token",
		Value:    MyToken.IDToken,
		HttpOnly: true,
		Secure:   true,
	})
	http.Redirect(w, r, requestedURI, http.StatusFound)
}

// (POST /core/)
func (Server) PostCore(w http.ResponseWriter, r *http.Request, params PostCoreParams) {
	// retriere info
	core_params, err := getRequestBody(r)
	if err {
		returnError(w, r, "Failed to read Request")
		return
	}

	// Create the core
	core := createCore(core_params)

	returnCreated(w, r, core)
}

// Delete the core configuration
// (DELETE /core/{id})
func (Server) DeleteCoreId(w http.ResponseWriter, r *http.Request, id Uuid, params DeleteCoreIdParams) {
	core := db[id]

	code, msg := deleteCore(id)

	// sanity checks
	switch code {
	case NOTFOUND:
		log.Println(msg)
		returnNotFound(w, r, Empty{})
		return
	case INVALIDSTATE:
		log.Println(msg)
		returnError(w, r, msg)
		return
	default:
		returnOk(w, r, core)
		return
	}
}

// Get core configuration
// (GET /core/{id})
func (Server) GetCoreId(w http.ResponseWriter, r *http.Request, id Uuid, params GetCoreIdParams) {
	core := db[id]

	if core == nil {
		log.Printf("core %s does not exist\n", id)
		returnNotFound(w, r, Empty{})
		return
	}
	if params.Action != nil {
		if *params.Action == Deploy {
			var state CoreState = Deploying
			core.State = &state

			deployCore(id)
		}
		if *params.Action == Stop {

			var state CoreState = Stopping
			core.State = &state

			stopCore(id)
		}
	}

	returnOk(w, r, core)
}

// Add a UE to the database
// (POST /core/{id}/UE)
func (Server) PostCoreIdUE(w http.ResponseWriter, r *http.Request, id Uuid, params PostCoreIdUEParams) {
}

// Get UE information
// (GET /core/{id}/UE/{imsi})
func (Server) GetCoreIdUEImsi(w http.ResponseWriter, r *http.Request, id Uuid, imsi Imsi, params GetCoreIdUEImsiParams) {
}

// Add a UE to the database
// (POST /core/{id}/UPF)
func (Server) PostCoreIdUPF(w http.ResponseWriter, r *http.Request, id Uuid, params PostCoreIdUPFParams) {
}

// List all cores
// (GET /cores/)
func (Server) GetCores(w http.ResponseWriter, r *http.Request, params GetCoresParams) {
	resp := db

	returnOk(w, r, resp)
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
	cookieInfo, error := getCookieInfo(r, w)
	if error {
		returnError(w, r, cookieInfo["error"])
		return
	}

	var token Token = cookieInfo["token"]
	resp := Tokenmap{
		Token: &token,
	}

	returnOk(w, r, resp)
}
