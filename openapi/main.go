package main

import (
	"log"
	"net/http"
	"time"

	"openapi/api"

	"github.com/gorilla/mux"
)

func main() {
	// create a type that satisfies the `api.ServerInterface`, which contains an implementation of every operation from the generated code
	server := api.NewServer()

	r := mux.NewRouter()
	// get an `http.Handler` that we can use
	handler := api.HandlerFromMux(server, r)

	srv := &http.Server{
		Handler:      handler,
		Addr:         ":8008",
		WriteTimeout: 15 * time.Second,
		ReadTimeout:  15 * time.Second,
	}
	log.Fatal(srv.ListenAndServe())

}
