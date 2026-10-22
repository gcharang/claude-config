# Incoherence Detection Skill

## Overview

Detects and resolves incoherence in documentation, code, and specs vs implementation.

## Interaction design

The resolution phase puts each fix to the user through AskUserQuestion, and the application phase
applies only the resolutions the user picks, so the user decides every change the workflow makes.
