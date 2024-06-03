package main

import (
	"log"
	"net/http"
	"os"
	"time"

	"openapi/api"

	"github.com/google/uuid"
	"github.com/gorilla/mux"
)

var (
	redirectURI  = os.Getenv("REDIRECT_URI")
	tokenURL     = os.Getenv("TOKEN_URL")
	oauthURL     = os.Getenv("OAUTH_URL")
	clientId     = os.Getenv("CLIENT_ID")
	clientSecret = os.Getenv("CLIENT_SECRET")
	basePath     = os.Getenv("BASE_PATH")
	port         = os.Getenv("PORT")
	rbacModel    = os.Getenv("RBAC_MODEL")
	rbacPolicy   = os.Getenv("RBAC_POLICY")
)

func setDefaults() {
	if len(port) == 0 {
		port = "8008"
	}

	if len(rbacPolicy) == 0 {
		rbacPolicy = "./policy.csv"
	}

	if len(rbacModel) == 0 {
		rbacModel = "./model.conf"
	}
}

func init() {
	setDefaults()
}

func main() {
	var serverId string = uuid.New().String() // generate a UUID

	// create a type that satisfies the `api.ServerInterface`, which contains an implementation of every operation from the generated code
	server := api.NewServer()

	r := mux.NewRouter()
	r = r.PathPrefix(basePath).Subrouter()

	middleware := api.MiddlewareCtx{Ctx: map[string]any{
		"model":  rbacModel,
		"policy": rbacPolicy}}
	middleware.Init()
	// Authentication
	r.Use(middleware.AuthMiddleware)
	// RBAC
	r.Use(middleware.RoleMiddleware)

	// get an `http.Handler` that we can use
	handler := api.HandlerFromMux(server, r)

	addr := ":" + port
	srv := &http.Server{
		Handler:      handler,
		Addr:         addr,
		WriteTimeout: 15 * time.Second,
		ReadTimeout:  15 * time.Second,
	}

	log.SetPrefix("server " + serverId + " ")
	log.Println("Started")
	log.Println("Listen on port " + port)
	log.Println("Base path " + basePath)

	log.Fatal(srv.ListenAndServe())
}
