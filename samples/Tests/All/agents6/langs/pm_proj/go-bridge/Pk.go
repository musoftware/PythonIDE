package main

import "github.com/google/uuid"

func info() string { return uuid.NewSHA1(uuid.NameSpaceDNS, []byte("rad")).String()[:8] }
