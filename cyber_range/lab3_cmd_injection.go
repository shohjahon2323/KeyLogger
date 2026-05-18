package main

import (
	"fmt"
	"net/http"
	"os/exec"
)

// CYBER RANGE LAB 3: Command Injection
func pingHandler(w http.ResponseWriter, r *http.Request) {
	ip := r.URL.Query().Get("ip")
	if ip == "" {
		fmt.Fprintf(w, "Please provide an IP. Example: /ping?ip=127.0.0.1")
		return
	}

	// VULNERABILITY: Directly passing user input to shell command
	cmdStr := "ping -c 1 " + ip
	out, err := exec.Command("sh", "-c", cmdStr).Output()
	
	if err != nil {
		fmt.Fprintf(w, "Error executing ping")
		return
	}

	fmt.Fprintf(w, "Ping Results:\n%s", string(out))
}

func main() {
	fmt.Println("[*] Cyber Range Lab 3: Starting Command Injection Lab on port 8081")
	http.HandleFunc("/ping", pingHandler)
	http.ListenAndServe(":8081", nil)
}
