procedure EnsureWorkspaceStructureAt(WorkspacePath: String);
begin
  if not DirExists(WorkspacePath) then
    EnsureDirectory(WorkspacePath);
  if not DirExists(AddBackslash(WorkspacePath) + 'Tagebuch') then
    EnsureDirectory(AddBackslash(WorkspacePath) + 'Tagebuch');
  if not DirExists(AddBackslash(WorkspacePath) + 'Temp') then
    EnsureDirectory(AddBackslash(WorkspacePath) + 'Temp');
  if not DirExists(AddBackslash(WorkspacePath) + 'Trashcan') then
    EnsureDirectory(AddBackslash(WorkspacePath) + 'Trashcan');
end;
