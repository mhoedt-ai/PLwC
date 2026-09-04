import assert from "node:assert/strict";
import test from "node:test";

import { plwcHostPriority, shouldClaimPlwcHost } from "./host-ownership";

const development = {
  extensionId: "nlogfcafjdfdoknpkbehjgihpafpipdb",
  packageVersion: "1.0.1",
};

test("the stable development extension replaces an unmarked legacy panel", () => {
  assert.equal(shouldClaimPlwcHost(development, null), true);
  assert.ok(plwcHostPriority(development.extensionId) > plwcHostPriority(undefined));
});

test("the stable development extension outranks an obsolete unpacked extension", () => {
  assert.equal(shouldClaimPlwcHost(development, {
    extensionId: "cjammbahoiopfjibogoofeamileannae",
    packageVersion: "0.2.0",
  }), true);
});

test("a store extension outranks the development extension", () => {
  assert.equal(shouldClaimPlwcHost({
    extensionId: "feceodobnhefdbfgmbinkndhogpfkicb",
    packageVersion: "1.0.0",
  }, development), true);
});

test("the same current extension keeps its existing panel", () => {
  assert.equal(shouldClaimPlwcHost(development, development), false);
});
