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
	RedirectURI  = os.Getenv("REDIRECT_URI")
	tokenURL     = os.Getenv("TOKEN_URL")
	oauthURL     = os.Getenv("OAUTH_URL")
	clientId     = os.Getenv("CLIENT_ID")
	clientSecret = os.Getenv("CLIENT_SECRET")
	basePath     = os.Getenv("BASE_PATH")
	port         = os.Getenv("PORT")
)

func setDefaults() {
	if len(port) == 0 {
		port = "8008"
	}
}

func main() {
	setDefaults()
	var serverId string = uuid.New().String() // generate a UUID

	// create a type that satisfies the `api.ServerInterface`, which contains an implementation of every operation from the generated code
	server := api.NewServer()

	r := mux.NewRouter()
	r = r.PathPrefix(basePath).Subrouter()
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
