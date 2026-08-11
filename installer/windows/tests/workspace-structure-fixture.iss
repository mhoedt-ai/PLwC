#ifndef OutputDir
#define OutputDir ".fixture-output"
#endif

[Setup]
AppId={{AC22D6A4-B4AD-4A45-9BE1-BFF3DF8F09AB}
AppName=PLwC Workspace Structure Fixture
AppVersion=1.0.0
CreateAppDir=no
DefaultDirName={tmp}
DisableFinishedPage=yes
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir={#OutputDir}
OutputBaseFilename=plwc-workspace-structure-fixture
Uninstallable=no

[Code]
procedure EnsureDirectory(Path: String);
begin
  if not ForceDirectories(Path) then
    RaiseException('Directory could not be created: ' + Path);
end;

#include "..\assets\workspace-structure.iss"

procedure CurStepChanged(CurStep: TSetupStep);
var
  WorkspacePath: String;
begin
  if CurStep = ssInstall then
  begin
    WorkspacePath := ExpandConstant('{param:WORKSPACEROOT|}');
    if WorkspacePath = '' then
      RaiseException('WORKSPACEROOT is required.');
    EnsureWorkspaceStructureAt(WorkspacePath);
  end;
end;
