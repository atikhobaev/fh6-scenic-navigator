//go:build !windows

package launcher_native

type noopProcessLifetime struct{}

func newProcessLifetime() (processLifetime, error)  { return &noopProcessLifetime{}, nil }
func (n *noopProcessLifetime) Assign(pid int) error { return nil }
func (n *noopProcessLifetime) Terminate() error     { return nil }
func (n *noopProcessLifetime) Close() error         { return nil }
