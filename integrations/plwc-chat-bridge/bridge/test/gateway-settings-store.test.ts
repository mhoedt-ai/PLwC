import assert from "node:assert/strict";
import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import test from "node:test";

import {
  assertActiveProfileStatus,
  type GatewaySettingsUpdate,
} from "../src/gateway-settings.js";
import {
  FileSystemGatewaySettingsStore,
  type GatewaySettingsPaths,
} from "../src/gateway-settings-store.js";

const settings: GatewaySettingsUpdate = {
  activeProfileName: "Sororitas",
  memoryWriteThreshold: "2",
  personaLayerDisabled: "false",
  personaWriteThreshold: "3",
  profilesPath: null,
  qdrantEnabled: "true",
  securityConfig: null,
  temperamentWriteThreshold: "2",
  workspacePath: "C:\\Users\\USER\\Claude_Arbeitsumgebung",
};

async function fixture(): Promise<{ root: string; paths: GatewaySettingsPaths }> {
  const root = await mkdtemp(join(tmpdir(), "plwc-settings-"));
  return {
    root,
    paths: {
      sharedSettings: join(root, "PLwC", "config", "gateway-settings.json"),
      activeProfileState: join(root, "PLwC", "config", "active_profile.json"),
      claudeMcpbSettings: join(
        root,
        "Claude",
        "Claude Extensions Settings",
        "local.mcpb.plwc.plwc-gateway.json",
      ),
    },
  };
}

test("persists editable settings without overwriting governed active profile state", async () => {
  const { root, paths } = await fixture();
  await mkdir(dirname(paths.claudeMcpbSettings), { recursive: true });
  await mkdir(dirname(paths.activeProfileState), { recursive: true });
  const governedState = {
    active_profile_name: "ZASA",
    plan_type: "profile_activation",
    schema_version: "1.0",
    updated_by: "plwc_governor_apply",
  };
  await writeFile(paths.activeProfileState, JSON.stringify(governedState));
  await writeFile(
    paths.claudeMcpbSettings,
    JSON.stringify({
      isEnabled: true,
      userConfig: {
        active_profile_name: "WasIstDas",
        unrelated_setting: "preserved",
      },
    }),
  );
  const store = new FileSystemGatewaySettingsStore(paths);

  try {
    await store.save(settings);
    assert.deepEqual(await store.load(), settings);

    const shared = JSON.parse(await readFile(paths.sharedSettings, "utf8"));
    assert.equal(shared.settings.active_profile_name, "Sororitas");
    assert.equal(shared.settings.temperament_write_threshold, 2);
    assert.equal(shared.settings.qdrant_enabled, true);
    assert.equal(shared.settings.persona_layer_disabled, false);
    assert.equal(shared.settings.profiles_path, null);

    const state = JSON.parse(await readFile(paths.activeProfileState, "utf8"));
    assert.deepEqual(state, governedState);

    const claude = JSON.parse(await readFile(paths.claudeMcpbSettings, "utf8"));
    assert.equal(claude.isEnabled, true);
    assert.equal(claude.userConfig.active_profile_name, "Sororitas");
    assert.equal(claude.userConfig.temperament_write_threshold, 2);
    assert.equal(claude.userConfig.qdrant_enabled, true);
    assert.equal(claude.userConfig.persona_layer_disabled, false);
    assert.equal(claude.userConfig.unrelated_setting, "preserved");
    assert.equal("profiles_path" in claude.userConfig, false);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test("clearing shared overrides preserves imported settings and governed profile state", async () => {
  const { root, paths } = await fixture();
  await mkdir(dirname(paths.claudeMcpbSettings), { recursive: true });
  await mkdir(dirname(paths.activeProfileState), { recursive: true });
  const imported = JSON.stringify({ isEnabled: true, userConfig: { active_profile_name: "Imported" } });
  const governedState = JSON.stringify({
    active_profile_name: "ZASA",
    plan_type: "profile_creation",
    schema_version: "1.0",
    updated_by: "plwc_governor_apply",
  });
  await writeFile(paths.claudeMcpbSettings, imported);
  await writeFile(paths.activeProfileState, governedState);
  const store = new FileSystemGatewaySettingsStore(paths);

  try {
    await store.save(settings);
    await store.clear();
    assert.equal(await store.load(), null);
    assert.equal(await readFile(paths.claudeMcpbSettings, "utf8").then((text) => JSON.parse(text).isEnabled), true);
    assert.equal(await readFile(paths.activeProfileState, "utf8"), governedState);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test("requires configured, resolved, active and path profile values to agree", () => {
  assert.doesNotThrow(() => assertActiveProfileStatus({
    active_profile_directory: "C:\\Users\\USER\\AppData\\Roaming\\PLwC\\profiles\\Sororitas",
    active_profile_name: "Sororitas",
    configured_active_profile: "Sororitas",
    profile_valid: true,
    resolved_active_profile: "Sororitas",
  }, "Sororitas"));

  assert.throws(() => assertActiveProfileStatus({
    active_profile_directory: "C:\\profiles\\WasIstDas",
    active_profile_name: "WasIstDas",
    configured_active_profile: "WasIstDas",
    profile_valid: true,
    resolved_active_profile: "WasIstDas",
  }, "Sororitas"));
});
