package api

import (
	"fmt"
	"log"

	"github.com/google/uuid"
)

var (
	_db = make(map[string]*Core)
)

// == Core functions ===========================================================
type CoreErrorCode int

const (
	CORE_OK CoreErrorCode = iota
	CORE_NOTFOUND
	CORE_INVALIDSTATE
)

func getCoreDb(id string) *Core {
	return _db[id]
}

func getCoresDb() map[string]*Core {
	return _db
}

func saveCoreDb(id string, core *Core) {
	_db[id] = core
}

func deleteCoreDb(id string) {
	delete(_db, id)
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

func deployCore(id string) {
	log.Println("should deploy the core ", id)
	core := getCoreDb(id)

	var state CoreState = Deployed
	core.State = &state
}

func stopCore(id string) {
	log.Println("should stop the core ", id)
	core := getCoreDb(id)

	var state CoreState = Stopped
	core.State = &state
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
