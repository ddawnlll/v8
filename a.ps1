Set-Location "C:\Users\dresden\Documents\v8"

git submodule deinit -f -- books

if (Test-Path ".git\modules\books") {
    Remove-Item -Recurse -Force ".git\modules\books"
}

if (Test-Path "books") {
    Remove-Item -Recurse -Force "books"
}

git submodule sync --recursive
git submodule update --init --recursive --progress -- books

git submodule status
Get-ChildItem books
