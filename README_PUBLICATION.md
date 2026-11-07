# ProTechStoneManager — GitHub publication

**Repository:** https://github.com/Abdealmalk007/ProTechStoneManager

**Version:** 2.0.0

**License:** MIT for original Abu Omar / ProTech code. Qt/PySide6 and other third-party packages retain their respective terms; consult THIRD_PARTY_NOTICES.md and LICENSE_SCOPE.md.

**Source:** Public on main with README and build instructions. The release ZIP includes the MIT LICENSE.

**Installer:** The supplied Setup.exe SHA-256 is e47ffc9ef5ecce1669bf53f344e268685cd50969733a58a64338bc645b2e9a1d. Authenticode status is **NotSigned**. It is retained in a **draft GitHub Release** only, pending qualified signing. It is not a published trusted Windows installer.

**Security:** No customer databases, orders, inventories, attachments, or private backups are included in the public source. A developer contact phone/email appears intentionally in application metadata.

**Release guard:** Inno Setup has a conditional code-signing configuration (`PROTECH_SIGNED_BUILD`/`ProTechSigner`). The GH workflow and PUBLISH_GITHUB.ps1 prevent auto-publication of unsigned Windows builds.
