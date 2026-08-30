package launcher_native

type processLifetime interface {
	Assign(pid int) error
	Terminate() error
	Close() error
}

type processLifetimeFactory func() (processLifetime, error)
