# GitHub distribution and Windows signing

Keep all source and eventual installers on GitHub. Before making a Windows Setup.exe publicly available, sign the application executables, Setup, and uninstall binaries with a trusted Code Signing certificate and timestamp. Run tools/Test-WindowsReleaseSignature.ps1 before publishing, and use tools/Publish-SignedWindowsRelease.ps1 to publish trusted Windows artifacts. Certificates and private keys must never be committed to Git.

Version v2.0.0 Setup.exe is currently NotSigned, so its release remains a draft on GitHub. Signing does not guarantee immediate SmartScreen reputation, and security mechanisms must not be disabled or bypassed.
