# Script de configuração do PostgreSQL para VAT Imposter
# Execute este script no PowerShell

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Configuração do PostgreSQL" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verificar se o PostgreSQL está instalado
Write-Host "Verificando se o PostgreSQL está instalado..." -ForegroundColor Yellow
try {
    $pgVersion = psql --version 2>$null
    if ($pgVersion) {
        Write-Host "✓ PostgreSQL encontrado: $pgVersion" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠ PostgreSQL não encontrado no PATH" -ForegroundColor Yellow
    Write-Host "  Certifique-se de que o PostgreSQL está instalado" -ForegroundColor Yellow
}

Write-Host ""

# Solicitar informações do banco de dados
Write-Host "Por favor, informe as configurações do PostgreSQL:" -ForegroundColor Cyan
Write-Host ""

$dbName = Read-Host "Nome do banco de dados [vatimposter]"
if ([string]::IsNullOrWhiteSpace($dbName)) {
    $dbName = "vatimposter"
}

$dbUser = Read-Host "Usuário do PostgreSQL [postgres]"
if ([string]::IsNullOrWhiteSpace($dbUser)) {
    $dbUser = "postgres"
}

$dbPassword = Read-Host "Senha do PostgreSQL" -AsSecureString
$dbPasswordPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($dbPassword)
)

$dbHost = Read-Host "Host [localhost]"
if ([string]::IsNullOrWhiteSpace($dbHost)) {
    $dbHost = "localhost"
}

$dbPort = Read-Host "Porta [5432]"
if ([string]::IsNullOrWhiteSpace($dbPort)) {
    $dbPort = "5432"
}

# Criar arquivo .env
Write-Host ""
Write-Host "Criando arquivo .env..." -ForegroundColor Yellow

$envContent = @"
# Configurações do Banco de Dados PostgreSQL
DB_NAME=$dbName
DB_USER=$dbUser
DB_PASSWORD=$dbPasswordPlain
DB_HOST=$dbHost
DB_PORT=$dbPort
"@

$envContent | Out-File -FilePath .env -Encoding utf8 -NoNewline

Write-Host "✓ Arquivo .env criado com sucesso!" -ForegroundColor Green
Write-Host ""

# Tentar criar o banco de dados
Write-Host "Deseja criar o banco de dados agora? (S/N)" -ForegroundColor Cyan
$createDb = Read-Host
if ($createDb -eq "S" -or $createDb -eq "s" -or $createDb -eq "Y" -or $createDb -eq "y") {
    Write-Host ""
    Write-Host "Criando banco de dados '$dbName'..." -ForegroundColor Yellow
    
    $env:PGPASSWORD = $dbPasswordPlain
    $createDbQuery = "CREATE DATABASE $dbName;"
    
    try {
        psql -U $dbUser -h $dbHost -p $dbPort -c $createDbQuery postgres 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Banco de dados criado com sucesso!" -ForegroundColor Green
        } else {
            Write-Host "⚠ Erro ao criar banco de dados. Pode já existir ou você não tem permissão." -ForegroundColor Yellow
            Write-Host "  Tente criar manualmente: CREATE DATABASE $dbName;" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "⚠ Erro ao executar comando. Crie o banco manualmente." -ForegroundColor Yellow
    }
    Remove-Item Env:\PGPASSWORD
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Próximos passos:" -ForegroundColor Cyan
Write-Host "1. Execute: python manage.py migrate" -ForegroundColor White
Write-Host "2. Execute: python manage.py populate_words" -ForegroundColor White
Write-Host "3. Execute: python manage.py runserver" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan



