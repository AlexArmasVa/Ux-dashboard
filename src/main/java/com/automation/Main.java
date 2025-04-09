package com.automation;

import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import java.io.BufferedReader;
import java.io.InputStreamReader;

public class Main {
    public static void main(String[] args) {
        // Start Chrome
        WebDriver driver = new ChromeDriver();

        // Open Google
        driver.get("https://www.google.com");

        // Print page title
        System.out.println("Page Title: " + driver.getTitle());

        // Close the browser
        driver.quit();

        // Run Python UX analysis
        runPythonScript();
    }

    private static void runPythonScript() {
        try {
            ProcessBuilder pb = new ProcessBuilder("python3", "analyze_ux.py");
            pb.redirectErrorStream(true);
            Process process = pb.start();

            // Read Python output
            BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
            String line;
            while ((line = reader.readLine()) != null) {
                System.out.println(line);
            }

            int exitCode = process.waitFor();
            System.out.println("\nPython script finished with exit code: " + exitCode);
        } catch (Exception e) {
            System.out.println("❌ Error running Python script: " + e.getMessage());
        }
    }
}