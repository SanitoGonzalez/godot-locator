# Godot Locator

<div align="center">
  <img src="website/static/img/godot-locator-logo-256.svg" alt="Godot Locator Banner">
</div>

A [Playwright](https://github.com/microsoft/playwright)-inspired locator API for runtime SceneTree of Godot games.

<div align="center">

[![godot-locator-cli](https://img.shields.io/badge/pypi-godot--locator--cli_v0.1.0-blue?logo=pypi&logoColor=white)](https://pypi.org/project/godot-locator-cli/)
[![godot-locator-mcp](https://img.shields.io/badge/pypi-godot--locator--mcp_v0.1.0-blue?logo=pypi&logoColor=white)](https://pypi.org/project/godot-locator-mcp/)
[![Godot Plugin](https://img.shields.io/badge/godot_plugin-v0.0.1-478CBF?logo=godot-engine&logoColor=white)](https://github.com/SanitoGonzalez/godot-locator)
[![Godot 4.x](https://img.shields.io/badge/godot-4.x-478CBF?logo=godot-engine&logoColor=white)](https://godotengine.org/)
[![Python](https://img.shields.io/badge/python-%E2%89%A53.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

</div>

## Why Godot Locator?

While writing games became easier thanks to coding agents, verification is still the bottleneck of game development process. Existing approaches either skip gameplay entirely or are too slow and expensive to run in a tight feedback loop.

|Types|Coverage|Cons|
|-----|--------|----|
|unit tests|pure logic|no scene/gameplay coverage|
|scripted tests|(limited) game play|changes break the test scenario|
|automated tests (screenshots + [VLM](https://en.wikipedia.org/wiki/Vision-language_model))|game play|slower and costs more than LLMs|
|automated tests (texts + [LLM](https://en.wikipedia.org/wiki/Large_language_model))|game play|no visual verification (See [hybrid workflow](#workflow-hybrid-testing-with-screenshots) as compensation)|

Godot Locator powers the last approach — a Playwright-style API over the live SceneTree that coding agents can drive directly.

## Features

## Quick Start

Copy the following prompt and paste to your coding agent:
```
Setup `Godot Locator CLI` referencing `https://github.com/SanitoGonzalez/godot-locator/tree/main/docs/how-to-setup-cli-for-agents.md`.
```

Then let them explore and interact with your Godot game:
```
Launch <path-to-godot-project> and click any button you see.
```

See [documentation](https://sanitogonzalez.github.io/godot-locator/) for the manual setup.

## Workflow:

## Workflow: hybrid testing with screenshots 


---

## Godot Locator Plugin

### Setup

### Key capabilities


## Godot Locator CLI

[Godot Locator CLI](https://sanitogonzalez.github.io/godot-locator/cli/) is a command-line interface for godot runtime automation designed for coding agents.

### Install

### Usage

## Godot Locator MCP

[Godot Locator MCP server](https://sanitogonzalez.github.io/godot-locator/mcp/) gives AI godot runtime control through the [Model Context Protocol](https://modelcontextprotocol.io).

### Setup

### Usage
