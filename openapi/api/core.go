package api

import (
	"database/sql"
	"encoding/json"
	"log"
	"os"

	"github.com/google/uuid"

	_ "github.com/mattn/go-sqlite3"
)

var (
	db     *sql.DB
	dbPath string
)

func init() {
	// load config
	dbPath = os.Getenv("DB_PATH")

	// set defaults
	if len(dbPath) == 0 {
		dbPath = "./db.db"
	}

	db = initDB()
}

// == CRUD DB operations =======================================================
func initDB() *sql.DB {
	//var err error
	db, err := sql.Open("sqlite3", dbPath)

	if err != nil {
		log.Fatal(err)
	}
	// defer sdb.Close()

	// Create the table in the database if it does not exist yet
	sts := `
		CREATE TABLE IF NOT EXISTS cores(id TEXT NOT NULL, settings TEXT, PRIMARY KEY (ID));
		`
	_, err = db.Exec(sts)
	if err != nil {
		log.Fatal(err)
	}

	return db
}

func getCore(id Uuid) *Core {
	stm, err := db.Prepare("SELECT * FROM cores WHERE id = ?")
	if err != nil {
		log.Println(err)
		return nil
	}
	defer stm.Close()

	var uid Uuid
	var settings string

	err = stm.QueryRow(id).Scan(&uid, &settings)

	if err != nil {
		log.Println(err)
		return nil
	}

	var core Core
	err = json.Unmarshal([]byte(settings), &core)
	if err != nil {
		log.Println(err)
		return nil
	}

	return &core
}

func getCores() map[Uuid]*Core {
	ret := make(map[string]*Core)

	rows, err := db.Query("SELECT * FROM cores;")

	if err != nil {
		log.Println(err)
		return nil
	}

	defer rows.Close()

	// TODO: check if possible to directly convert the full answer to a map
	// instead of iterating manually
	var uid Uuid
	var settings string
	for rows.Next() {
		err = rows.Scan(&uid, &settings)

		if err != nil {
			log.Println(err)
			return nil
		}

		var core Core
		err = json.Unmarshal([]byte(settings), &core)
		if err != nil {
			log.Println(err)
			return nil
		}

		ret[uid] = &core
	}

	return ret
}

func createCore(id Uuid, core *Core) {
	stm, err := db.Prepare("INSERT INTO Cores(id, settings) VALUES (?, ?);")
	if err != nil {
		log.Println(err)
		return
	}
	defer stm.Close()

	b, _ := json.Marshal(core)

	_, err = stm.Exec(id, string(b))
	if err != nil {
		log.Println(err)
		return
	}
}

func updateCore(id Uuid, core *Core) {
	stm, err := db.Prepare("UPDATE cores SET settings = ? WHERE id = ?")
	if err != nil {
		log.Println(err)
		return
	}
	defer stm.Close()

	b, _ := json.Marshal(core)

	_, err = stm.Exec(string(b), id)
	if err != nil {
		log.Println(err)
		return
	}
}

func deleteCore(id Uuid) {
	stm, err := db.Prepare("DELETE FROM cores WHERE id = ?")
	if err != nil {
		log.Println(err)
		return
	}
	defer stm.Close()

	_, err = stm.Exec(id)
	if err != nil {
		log.Println(err)
		return
	}
}

// == Core functions ===========================================================
type CoreErrorCode int

const (
	CORE_OK CoreErrorCode = iota
	CORE_NOTFOUND
	CORE_INVALIDSTATE
)

func GetCore(id Uuid) *Core {
	return getCore(id)
}

func GetCores() map[Uuid]*Core {
	return getCores()
}

func CreateCore(core_params *CoreParams) *Core {
	var id Uuid = uuid.New().String()
	var state CoreState = Created
	nfs := new(NetworkFunctions)

	core := Core{
		NetworkFunctions: nfs,
		Parameters:       core_params,
		Uuid:             &id,
		State:            &state,
	}

	createCore(id, &core)
	return &core
}

func DeployCore(id Uuid) *Core {
	log.Println("should deploy the core ", id)
	core := GetCore(id)

	var state CoreState = Deployed
	core.State = &state

	updateCore(id, core)

	return core
}

func StopCore(id Uuid) *Core {
	log.Println("should stop the core ", id)
	core := GetCore(id)

	var state CoreState = Stopped
	core.State = &state

	updateCore(id, core)

	return core
}

func DeleteCore(id Uuid) CoreErrorCode {
	core := GetCore(id)

	// sanity checks
	if core == nil {
		return CORE_NOTFOUND
	}
	if *core.State != Stopped {
		return CORE_INVALIDSTATE
	}

	deleteCore(id)

	return CORE_OK
}
