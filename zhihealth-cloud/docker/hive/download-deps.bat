@echo off
REM ZhiHealth Hive Stack - Download dependencies locally
REM Run this script first before docker-compose build

set DOWNLOAD_DIR=e:\Health\zhihealth-cloud\docker\hive\downloads
if not exist "%DOWNLOAD_DIR%" mkdir "%DOWNLOAD_DIR%"

echo ============================================
echo  Downloading Hadoop 3.3.4...
echo ============================================
if not exist "%DOWNLOAD_DIR%\hadoop-3.3.4.tar.gz" (
    echo Downloading from Apache archive...
    curl -L --connect-timeout 120 --retry 5 -o "%DOWNLOAD_DIR%\hadoop-3.3.4.tar.gz" "https://downloads.apache.org/hadoop/common/hadoop-3.3.4/hadoop-3.3.4.tar.gz"
) else (
    echo Hadoop already downloaded.
)

echo.
echo ============================================
echo  Downloading Hive 3.1.3...
echo ============================================
if not exist "%DOWNLOAD_DIR%\apache-hive-3.1.3-bin.tar.gz" (
    echo Downloading from Apache archive...
    curl -L --connect-timeout 120 --retry 5 -o "%DOWNLOAD_DIR%\apache-hive-3.1.3-bin.tar.gz" "https://downloads.apache.org/hive/hive-3.1.3/apache-hive-3.1.3-bin.tar.gz"
) else (
    echo Hive already downloaded.
)

echo.
echo ============================================
echo  Downloading MySQL JDBC Driver...
echo ============================================
if not exist "%DOWNLOAD_DIR%\mysql-connector-java.jar" (
    curl -L -o "%DOWNLOAD_DIR%\mysql-connector-java.jar" "https://repo1.maven.org/maven2/mysql/mysql-connector-java/8.0.33/mysql-connector-java-8.0.33.jar"
) else (
    echo MySQL driver already downloaded.
)

echo.
echo ============================================
echo  Verifying downloads...
echo ============================================
dir "%DOWNLOAD_DIR%" /B

echo.
echo Done! Now run: docker-compose -f docker-compose.hive.yml up -d --build
