package api

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"

	"github.com/google/uuid"

	_ "github.com/mattn/go-sqlite3"
)

var sdb *sql.DB

func init() {
	var err error
	sdb, err = sql.Open("sqlite3", "./cores.db")

	if err != nil {
		log.Fatal(err)
	}
	// defer sdb.Close()

	// Create the table in the database if it does not exist yet
	sts := `
		CREATE TABLE IF NOT EXISTS cores(id TEXT NOT NULL, settings TEXT, PRIMARY KEY (ID));
		`
	_, err = sdb.Exec(sts)
	if err != nil {
		log.Fatal(err)
	}
}

// == Core functions ===========================================================
type CoreErrorCode int

const (
	CORE_OK CoreErrorCode = iota
	CORE_NOTFOUND
	CORE_INVALIDSTATE
)

func getCoreDb(id Uuid) *Core {
	stm, err := sdb.Prepare("SELECT * FROM cores WHERE id = ?")
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

func getCoresDb() map[string]*Core {
	ret := make(map[string]*Core)

	rows, err := sdb.Query("SELECT * FROM cores;")

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

func saveCoreDb(id string, core *Core) {
	stm, err := sdb.Prepare("INSERT INTO Cores(id, settings) VALUES (?, ?);")
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

func updateCoreDb(id string, core *Core) {
	stm, err := sdb.Prepare("UPDATE cores SET settings = ? WHERE id = ?")
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

func deleteCoreDb(id string) {
	stm, err := sdb.Prepare("DELETE FROM cores WHERE id = ?")
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

func CreateCore(core_params CoreParams) Core {
	var id Uuid = uuid.New().String()
	var state CoreState = Created
	nfs := new(NetworkFunctions)

	core := Core{
		NetworkFunctions: nfs,
		Parameters:       &core_params,
		Uuid:             &id,
		State:            &state,
	}

	saveCoreDb(id, &core)
	return core
}

func deployCore(id string) *Core {
	log.Println("should deploy the core ", id)
	core := getCoreDb(id)

	var state CoreState = Deployed
	core.State = &state

	updateCoreDb(id, core)

	return core
}

func stopCore(id string) *Core {
	log.Println("should stop the core ", id)
	core := getCoreDb(id)

	var state CoreState = Stopped
	core.State = &state

	updateCoreDb(id, core)

	return core
}

func deleteCore(id string) (CoreErrorCode, string) {
	core := getCoreDb(id)

	// sanity checks
	if core == nil {
		msg := fmt.Sprintf("core %s does not exist", id)
		return CORE_NOTFOUND, msg
	}
	if *core.State != Stopped {
		msg := fmt.Sprintf("trying to delete core %s that is not stopped", id)
		return CORE_INVALIDSTATE, msg
	}

	deleteCoreDb(id)

	return CORE_OK, fmt.Sprintf("core %s deleted", id)
}
