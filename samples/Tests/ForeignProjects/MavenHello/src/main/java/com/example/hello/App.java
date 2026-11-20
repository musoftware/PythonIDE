package com.example.hello;

/** Maven quickstart-style application. */
public class App {
    static int square(int x) {
        int result = x * x;
        return result;
    }

    public static void main(String[] args) {
        System.out.println("Hello from Maven! 7^2 = " + square(7));
    }
}
