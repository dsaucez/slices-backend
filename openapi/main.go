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

type BackendServer struct {
	Server   *http.Server
	Router   *mux.Router
	serverId string
}

var (
	basePath = os.Getenv("BASE_PATH")
	port     = os.Getenv("PORT")
)

func setDefaults() {
	if len(port) == 0 {
		port = "8008"
	}
}

func init() {
	setDefaults()
}

func (backend *BackendServer) Initialize() {
	// create a type that satisfies the `api.ServerInterface`, which contains an implementation of every operation from the generated code
	server := api.NewServer()

	backend.Router = mux.NewRouter()
	backend.Router = backend.Router.PathPrefix(basePath).Subrouter()

	// // Authentication
	// backend.Router.Use(api.AuthMiddleware)
	// // RBAC
	// backend.Router.Use(api.RoleMiddleware)

	// get an `http.Handler` that we can use
	handler := api.HandlerFromMux(server, backend.Router)

	addr := ":" + port
	backend.Server = &http.Server{
		Handler:      handler,
		Addr:         addr,
		WriteTimeout: 15 * time.Second,
		ReadTimeout:  15 * time.Second,
	}
}

func (backend *BackendServer) Run() {

	log.Println("Starting")
	log.Println("Listen on port " + port)
	log.Println("Base path " + basePath)

	log.Fatal(backend.Server.ListenAndServe())
}

func main() {
	var backend BackendServer

	backend.serverId = uuid.New().String() // generate a UUID

	log.SetPrefix("server " + backend.serverId + " ")
	backend.Initialize()
	backend.Run()
}
