package main

import (
	"bytes"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
)

var backend BackendServer

var token string

func init() {
	token = os.Getenv("TOKEN")
}

func executeRequest(req *http.Request, withToken bool) *httptest.ResponseRecorder {
	rr := httptest.NewRecorder()

	if withToken {
		cookie := fmt.Sprintf("token=%s;", token)
		req.Header.Add("Cookie", cookie)
	}
	backend.Router.ServeHTTP(rr, req)

	return rr
}

func checkResponseCode(t *testing.T, expected, actual int) {
	if expected != actual {
		t.Errorf("Expected response code %d. Got %d\n", expected, actual)
	}
}

func TestMain(m *testing.M) {
	backend.Initialize()
	code := m.Run()
	os.Exit(code)
}

func TestHealthz(t *testing.T) {
	req, _ := http.NewRequest("GET", "/healthz", nil)
	response := executeRequest(req, false)

	checkResponseCode(t, http.StatusOK, response.Code)
}

func TestCores(t *testing.T) {
	req, _ := http.NewRequest("GET", "/cores/", nil)

	response := executeRequest(req, true)

	fmt.Println(response.Body)
	checkResponseCode(t, http.StatusOK, response.Code)
}

func TestPostCore(t *testing.T) {
	body := []byte(`	{
    "mcc": "001",
    "mnc": "01",
    "tac": "0x0001",
    "dnns": [
        {
            "dnn": "internet",
            "pdu_session_type": "IPv4",
            "ipv4_subnet": "192.0.2.0/24"
        }
    ],
    "slices": [
        {
            "snssai": {
                "sst": 2,
                "sd": "FFFFFF"
            },
            "dnns": [
                "internet"
            ],
            "qos_profile": {
                "5qi": 5,
                "session_ambr_ul": "200Mbps",
                "session_ambr_dl": "200Mbps"
            }
        }
    ]
	}`)
	req, _ := http.NewRequest("POST", "/core/", bytes.NewBuffer(body))
	req.Header.Add("Content-Type", "application/json")

	response := executeRequest(req, true)

	checkResponseCode(t, http.StatusCreated, response.Code)
}

func TestCores2(t *testing.T) {
	req, _ := http.NewRequest("GET", "/cores/", nil)

	response := executeRequest(req, true)

	fmt.Println(response.Body)
	checkResponseCode(t, http.StatusOK, response.Code)
}

func TestLougout(t *testing.T) {
	req, _ := http.NewRequest("GET", "/logout", nil)
	response := executeRequest(req, true)

	checkResponseCode(t, http.StatusOK, response.Code)
}
