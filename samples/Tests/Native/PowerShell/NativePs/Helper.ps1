# Module Helper.
function Greet($name) {
    return "Hello, $name!"
}

function Shout($name) {
    return (Greet $name).ToUpperInvariant()
}
