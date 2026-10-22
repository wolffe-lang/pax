//! The Unix wolf driver's link-only cc argument subset, not a C compiler.
use std::ffi::OsString;
use std::os::unix::process::CommandExt;
use std::path::PathBuf;
use std::process::Command;

fn translate(args: impl IntoIterator<Item = OsString>) -> Vec<OsString> {
    let mut out = Vec::new();
    let mut output_name = false;
    for arg in args {
        if output_name {
            out.push(arg);
            output_name = false;
            continue;
        }
        match arg.to_str() {
            Some("-o") => { out.push(arg); output_name = true; }
            Some("-lpthread" | "-ldl" | "-lm") => {} // musl's libc.a owns these interfaces
            Some(s) if s.starts_with("-fuse-ld=") => {}
            Some(s) if s.starts_with("-Wl,") => out.extend(s[4..].split(',').map(OsString::from)),
            _ => out.push(arg),
        }
    }
    out
}

fn main() {
    let root = PathBuf::from(std::env::var_os("PAX_CC_SYSROOT").unwrap_or_else(|| "/usr/lib/wolf-musl".into()));
    let linker = std::env::var_os("PAX_LLD").unwrap_or_else(|| "/usr/bin/ld.lld".into());
    let mut cmd = Command::new(linker);
    cmd.args(["--threads=1", "--no-mmap-output-file", "-static"])
        .arg(root.join("crt1.o")).arg(root.join("crti.o"))
        .arg("--start-group").args(translate(std::env::args_os().skip(1)))
        .arg(root.join("libc.a")).arg(root.join("libunwind.a"))
        .arg("--end-group").arg(root.join("crtn.o"));
    let error = cmd.exec();
    eprintln!("pax-cc: cannot execute the linker: {error}");
    std::process::exit(127);
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn linker_looking_output_names_are_values() {
        for name in ["-lpthread", "-Wl,artifact", "-fuse-ld=artifact"] {
            let input = ["-o", name, "one.o", "-Wl,--gc-sections"].map(OsString::from);
            let want = ["-o", name, "one.o", "--gc-sections"].map(OsString::from);
            assert_eq!(translate(input), want);
        }
    }

    #[test]
    fn translate_the_driver_without_shell_parsing() {
        let input = ["-o", "a name;not-a-command", "one.o", "libwolf_rt.a", "-lpthread", "-ldl", "-lm",
                     "-Wl,--gc-sections", "-Wl,--defsym=wolf_trap=__wolf_rt_trap_at", "-fuse-ld=lld"];
        let got = translate(input.map(OsString::from));
        let want = ["-o", "a name;not-a-command", "one.o", "libwolf_rt.a", "--gc-sections",
                    "--defsym=wolf_trap=__wolf_rt_trap_at"].map(OsString::from);
        assert_eq!(got, want);
    }
}
